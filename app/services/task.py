import math
import os.path
import re
from os import path

from loguru import logger

from app.config import config
from app.models import const
from app.models.schema import VideoParams, VideoConcatMode, VideoParagraph
from app.services import llm, material, voice, video, subtitle
from app.services import state as sm
from app.services.llm import generate_terms_baidu
from app.utils import utils


def start(task_id, params: VideoParams):
    """
    {
        "video_subject": "",
        "video_aspect": "横屏 16:9（西瓜视频）",
        "voice_name": "女生-晓晓",
        "enable_bgm": false,
        "font_name": "STHeitiMedium 黑体-中",
        "text_color": "#FFFFFF",
        "font_size": 60,
        "stroke_color": "#000000",
        "stroke_width": 1.5
    }
    """
    logger.info(f"start task: {task_id}")
    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=5)


    video_subject = params.video_subject
    voice_name = voice.parse_voice_name(params.voice_name)
    paragraph_number = params.paragraph_number
    n_threads = params.n_threads
    max_clip_duration = params.video_clip_duration

    # step 0, generate video script
    logger.info("\n\n## generating video script")
    video_script = params.video_script.strip()
    if not video_script:
        video_script = llm.generate_script(video_subject=video_subject, language=params.video_language,
                                           paragraph_number=paragraph_number)
    else:
        logger.debug(f"video script: \n{video_script}")

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=10)

    # step 1, generate audio
    logger.info("\n\n## generating audio")
    audio_file = path.join(utils.task_dir(task_id), f"audio.mp3")
    sub_maker = voice.tts(text=video_script, voice_name=voice_name, voice_file=audio_file)
    if sub_maker is None:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error(
            "failed to generate audio, maybe the network is not available. if you are in China, please use a VPN.")
        return

    audio_duration = voice.get_audio_duration(sub_maker)
    audio_duration = math.ceil(audio_duration)

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=30)

    # step 2, generate subtitle
    subtitle_path = ""
    sub_titles = []
    if params.subtitle_enabled:
        subtitle_path = path.join(utils.task_dir(task_id), f"subtitle.srt")
        subtitle_provider = config.app.get("subtitle_provider", "").strip().lower()
        logger.info(f"\n\n## generating subtitle, provider: {subtitle_provider}")
        subtitle_fallback = False
        if subtitle_provider == "edge":
            sub_titles = voice.create_subtitle(text=video_script, sub_maker=sub_maker, subtitle_file=subtitle_path)
            if not os.path.exists(subtitle_path):
                subtitle_fallback = True
                logger.warning("subtitle file not found, fallback to whisper")

        if subtitle_provider == "whisper" or subtitle_fallback:
            sub_titles = subtitle.create(audio_file=audio_file, subtitle_file=subtitle_path)
            logger.info("\n\n## correcting subtitle")
            subtitle.correct(subtitle_file=subtitle_path, video_script=video_script)

        subtitle_lines = subtitle.file_to_subtitles(subtitle_path)
        if not subtitle_lines:
            logger.warning(f"subtitle file is invalid: {subtitle_path}")
            subtitle_path = ""

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=40)
    logger.info(f"\n\n## generating sub_titles: {sub_titles}")

    # step 3, generate video terms
    logger.info("\n\n## generating video terms ")
    video_terms = params.video_terms
    if not video_terms:
        video_terms = llm.generate_terms(video_subject=video_subject, video_script=video_script, amount=5,sub_titles=sub_titles,language=params.video_language)
    else:
        if isinstance(video_terms, str):
            video_terms = [term.strip() for term in re.split(r'[\n]', video_terms)]
        elif isinstance(video_terms, list):
            video_terms = [term.strip() for term in video_terms]
        else:
            raise ValueError("video_terms must be a string or a list of strings.")

        logger.debug(f"video terms: {utils.to_json(video_terms)}")

    script_file = path.join(utils.task_dir(task_id), f"script.json")
    script_lines = generate_terms_baidu(video_subject, video_script, 5)
    paragraph = []
    for sub_title in sub_titles:
        for i, line in enumerate(script_lines):
            if line.replace("）","").endswith(sub_title['msg']):
                item = VideoParagraph()
                item.text = video_terms[i]
                item.end_time = int(sub_title["end_time"])
                if len(paragraph) > 0:
                    item.duration = int((item.end_time - paragraph[-1].end_time)/10000000)
                else:
                    item.duration = item.end_time
                paragraph.append(item)
                logger.debug(
                    f"paragraph:{i}, {item.text} ,end_time: {item.end_time}, duration: {item.duration}")

    logger.debug(f"video_terms: {video_terms} {type(video_terms)}")

    script_data = {
        "script": video_script,
        "search_terms": video_terms,
        "params": params,
    }

    with open(script_file, "w", encoding="utf-8") as f:
        f.write(utils.to_json(script_data))

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=20)

    # step 4, download videos
    logger.info("\n\n## downloading videos")
    downloaded_videos = material.download_videos(task_id=task_id,
                                                 search_terms=paragraph,
                                                 video_aspect=params.video_aspect,
                                                 video_contact_mode=params.video_concat_mode,
                                                 audio_duration=audio_duration * params.video_count,
                                                 max_clip_duration=max_clip_duration,
                                                 )
    if not downloaded_videos:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error(
            "failed to download videos, maybe the network is not available. if you are in China, please use a VPN.")
        return

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=50)

    final_video_paths = []
    combined_video_paths = []
    video_concat_mode = params.video_concat_mode
    if params.video_count > 1:
        video_concat_mode = VideoConcatMode.random

    _progress = 50
    for i in range(params.video_count):
        index = i + 1
        combined_video_path = path.join(utils.task_dir(task_id), f"combined-{index}.mp4")
        logger.info(f"\n\n## combining video: {index} => {combined_video_path}")
        video.combine_videos(combined_video_path=combined_video_path,
                             video_paths=downloaded_videos,
                             audio_file=audio_file,
                             video_aspect=params.video_aspect,
                             video_concat_mode=video_concat_mode,
                             max_clip_duration=max_clip_duration,
                             threads=n_threads)

        _progress += 50 / params.video_count / 2
        sm.state.update_task(task_id, progress=_progress)

        final_video_path = path.join(utils.task_dir(task_id), f"final-{index}.mp4")

        logger.info(f"\n\n## generating video: {index} => {final_video_path}")
        # Put everything together
        video.generate_video(video_path=combined_video_path,
                             audio_path=audio_file,
                             subtitle_path=subtitle_path,
                             output_file=final_video_path,
                             params=params,
                             )

        _progress += 50 / params.video_count / 2
        sm.state.update_task(task_id, progress=_progress)

        final_video_paths.append(final_video_path)
        combined_video_paths.append(combined_video_path)

    logger.success(f"task {task_id} finished, generated {len(final_video_paths)} videos.")

    kwargs = {
        "videos": final_video_paths,
        "combined_videos": combined_video_paths
    }
    sm.state.update_task(task_id, state=const.TASK_STATE_COMPLETE, progress=100, **kwargs)
    return kwargs


# def start_test(task_id, params: VideoParams):
#     print(f"start task {task_id} \n")
#     time.sleep(5)
#     print(f"task {task_id} finished \n")

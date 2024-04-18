import os
import random
from urllib.parse import urlencode

import requests
from typing import List
from loguru import logger

from app.config import config
from app.models.schema import VideoAspect, VideoConcatMode, MaterialInfo, VideoParagraph
from app.utils import utils

requested_count = 0


def round_robin_api_key():
    pexels_api_keys = config.app.get("pexels_api_keys")
    if not pexels_api_keys:
        raise ValueError(
            f"\n\n##### pexels_api_keys is not set #####\n\nPlease set it in the config.toml file: {config.config_file}\n\n{utils.to_json(config.app)}")

    # if only one key is provided, return it
    if isinstance(pexels_api_keys, str):
        return pexels_api_keys

    global requested_count
    requested_count += 1
    return pexels_api_keys[requested_count % len(pexels_api_keys)]


def search_videos(search_term: str,
                  duration: int,
                  video_aspect: VideoAspect = VideoAspect.portrait,
                  ) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_orientation = aspect.name
    video_width, video_height = aspect.to_resolution()
    return search_videos_baidu(search_term, duration, video_aspect)
    headers = {
        "Authorization": round_robin_api_key()
    }
    proxies = config.pexels.get("proxies", None)
    # Build URL
    params = {
        "query": search_term,
        "per_page": 20,
        "orientation": video_orientation
    }
    query_url = f"https://api.pexels.com/videos/search?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with proxies: {proxies}")

    try:
        r = requests.get(query_url, headers=headers, proxies=proxies, verify=False, timeout=(30, 60))
        response = r.json()
        video_items = []
        if "videos" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["videos"]
        # loop through each video in the result
        total_duration = 0
        for v in videos:
            o_duration = v["duration"]
            # check if video has desired minimum duration
            if o_duration < duration:
                continue
            video_files = v["video_files"]
            # loop through each url to determine the best quality
            for video in video_files:
                w = int(video["width"])
                h = int(video["height"])
                if w == video_width and h == video_height:
                    item = MaterialInfo()
                    item.provider = "pexels"
                    item.url = video["link"]
                    item.duration = o_duration
                    video_items.append(item)
                    total_duration += int(o_duration)
                    if total_duration >= duration:
                        break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_videos_baidu(search_term: str,
                  duration: int,
                  video_aspect: VideoAspect = VideoAspect.portrait,
                  ) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_orientation = aspect.name
    video_width, video_height = aspect.to_resolution()
    if not search_term or len(search_term)==0:
        return list()
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': 'BIDUPSID=51969EAA2FF042ECDDBAC5A35A23FA83; PSTM=1710849045; BAIDUID=51969EAA2FF042ECBCBE5181F584BCA3:FG=1; BDUSS=2xBUkZVT1k0djJvd2lZU0FBdEh6Rnc0d1FtNTlBMTcwWDRYcDVydFUxMWpJaWxtRVFBQUFBJCQAAAAAAAAAAAEAAACx3n5CUVHIurbsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGOVAWZjlQFmd; BDUSS_BFESS=2xBUkZVT1k0djJvd2lZU0FBdEh6Rnc0d1FtNTlBMTcwWDRYcDVydFUxMWpJaWxtRVFBQUFBJCQAAAAAAAAAAAEAAACx3n5CUVHIurbsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGOVAWZjlQFmd; H_WISE_SIDS_BFESS=40171_40080_40380_40368_40401_40415_40299_40464_40459_39662_40505_40512_40397_40445_60037_60029_60035_60048_40511_60087; H_PS_PSSID=40171_40380_40368_40401_40415_40299_40459_39662_40505_40512_40397_40445_60037_60029_60035_60048_40511; H_WISE_SIDS=40171_40380_40368_40401_40415_40299_40459_39662_40505_40512_40397_40445_60037_60029_60035_60048_40511; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; ab_sr=1.0.1_NmQwZWMyMjJmMzg3YWI5N2JkNjc1ZTc5MDcwOTFlOGQwZjBmNDFlZjc2MTlkNjlmNWMxOGEyM2E4ZWRlNWY5MzEzYjEyNTVmNTQwNjdkOTQ3OTY4ZDMyMWVmOTM3MGU5NDlkZThlYzQ2NWU0ZmNiNjljMTVhYjVjODhkNTNjMTczODg0ZjRmN2QxODljMDBlM2M4ZTE5OTVjNTBhN2U2NmJlNjk2YjlhODcwNWFkMzczYWU2NmI5ODFiZmMxODIy; BAIDUID_BFESS=51969EAA2FF042ECBCBE5181F584BCA3:FG=1; BA_HECTOR=01202h0la524aha1058k05803d8cr41j1la0b1t; ZFY=AgeEZXgSQQsWow5HZuyOCDqZZ4eE8t:ASHy9PbLgSHsg:C; delPer=0; PSINO=1; Hm_lvt_400790f61cbe0e7d1d9cae19d202e8ce=1711379754,1713023110; Hm_lpvt_400790f61cbe0e7d1d9cae19d202e8ce=1713023110; RT="z=1&dm=baidu.com&si=327cfb33-b024-4fa1-8439-88075e18a14d&ss=luy8zkp8&sl=e&tt=bao&bcn=https%3A%2F%2Ffclog.baidu.com%2Flog%2Fweirwood%3Ftype%3Dperf&ld=r2qv"',
        'Referer': 'https://aigc.baidu.com/builder/aigc?source=sass_pc_upload&from=bjh&startbyid=1713023109530&ttvId=1713023109357462514&__spa__=1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    proxies = config.pexels.get("proxies", None)
    # Build URL

    params = {
        'text': search_term,
        'type': 'video',
        'duration': '0',
        # 'rankCategory': '影视,影视资讯',
        'plateType': '1',
        'materialSource': '0',
    }

    query_url = f"https://aigc.baidu.com/aigc/saas/pc/v1/assist/searchList?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with target_duration: {duration}")

    try:
        r = requests.get(query_url, headers=headers, proxies=proxies, verify=False)
        res = r.json()
        response = res["data"]
        video_items = []
        if "material" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["material"][0]["list"]
        minimum_duration = 3
        total_duration = 0
        for v in videos:
            if v["duration"] < minimum_duration:
                continue
            item = MaterialInfo()
            item.provider = "baidu"
            item.url =v["url"]
            item.duration = v["duration"]
            item.size = v["definition"].replace("P", "")
            video_items.append(item)
            total_duration += int(item.duration)
            logger.debug(
                f"video: {item.url} ,duration: {item.duration}, total_duration: {total_duration}")
            if total_duration >= duration:
                break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_images_baidu(search_term: str,
                  minimum_duration: int,
                  video_aspect: VideoAspect = VideoAspect.portrait,
                  ) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_orientation = aspect.name
    video_width, video_height = aspect.to_resolution()
    if not search_term or len(search_term)==0:
        return list()
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': 'BIDUPSID=51969EAA2FF042ECDDBAC5A35A23FA83; PSTM=1710849045; BAIDUID=51969EAA2FF042ECBCBE5181F584BCA3:FG=1; BDUSS=2xBUkZVT1k0djJvd2lZU0FBdEh6Rnc0d1FtNTlBMTcwWDRYcDVydFUxMWpJaWxtRVFBQUFBJCQAAAAAAAAAAAEAAACx3n5CUVHIurbsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGOVAWZjlQFmd; BDUSS_BFESS=2xBUkZVT1k0djJvd2lZU0FBdEh6Rnc0d1FtNTlBMTcwWDRYcDVydFUxMWpJaWxtRVFBQUFBJCQAAAAAAAAAAAEAAACx3n5CUVHIurbsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGOVAWZjlQFmd; H_WISE_SIDS_BFESS=40171_40080_40380_40368_40401_40415_40299_40464_40459_39662_40505_40512_40397_40445_60037_60029_60035_60048_40511_60087; H_PS_PSSID=40171_40380_40368_40401_40415_40299_40459_39662_40505_40512_40397_40445_60037_60029_60035_60048_40511; H_WISE_SIDS=40171_40380_40368_40401_40415_40299_40459_39662_40505_40512_40397_40445_60037_60029_60035_60048_40511; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; ab_sr=1.0.1_NmQwZWMyMjJmMzg3YWI5N2JkNjc1ZTc5MDcwOTFlOGQwZjBmNDFlZjc2MTlkNjlmNWMxOGEyM2E4ZWRlNWY5MzEzYjEyNTVmNTQwNjdkOTQ3OTY4ZDMyMWVmOTM3MGU5NDlkZThlYzQ2NWU0ZmNiNjljMTVhYjVjODhkNTNjMTczODg0ZjRmN2QxODljMDBlM2M4ZTE5OTVjNTBhN2U2NmJlNjk2YjlhODcwNWFkMzczYWU2NmI5ODFiZmMxODIy; BAIDUID_BFESS=51969EAA2FF042ECBCBE5181F584BCA3:FG=1; BA_HECTOR=01202h0la524aha1058k05803d8cr41j1la0b1t; ZFY=AgeEZXgSQQsWow5HZuyOCDqZZ4eE8t:ASHy9PbLgSHsg:C; delPer=0; PSINO=1; Hm_lvt_400790f61cbe0e7d1d9cae19d202e8ce=1711379754,1713023110; Hm_lpvt_400790f61cbe0e7d1d9cae19d202e8ce=1713023110; RT="z=1&dm=baidu.com&si=327cfb33-b024-4fa1-8439-88075e18a14d&ss=luy8zkp8&sl=e&tt=bao&bcn=https%3A%2F%2Ffclog.baidu.com%2Flog%2Fweirwood%3Ftype%3Dperf&ld=r2qv"',
        'Referer': 'https://aigc.baidu.com/builder/aigc?source=sass_pc_upload&from=bjh&startbyid=1713023109530&ttvId=1713023109357462514&__spa__=1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    proxies = config.pexels.get("proxies", None)
    # Build URL

    params = {
        'query': search_term,
        'size': 20,
        'offset': 0
    }

    query_url = f"https://aigc.baidu.com/aigc/bjh/pc/v1/assist/searchBdimg?{urlencode(params)}"
    logger.info(f"searching images: {query_url}")

    try:
        r = requests.get(query_url, headers=headers, proxies=proxies, verify=False)
        res = r.json()
        response = res["data"]
        image_items = []
        if "list" not in response:
            logger.error(f"search images failed: {response}")
            return image_items
        images = response["list"]
        for v in images:
            item = MaterialInfo()
            item.provider = "baidu"
            item.url =v["image"] + "."+ v["imgType"]
            item.size = v["imageSize"] #1080*1920
            item.description = v["name"].replace("<strong>", "").replace("</strong>", "")
            image_items.append(item)

        return image_items
    except Exception as e:
        logger.error(f"search images failed: {str(e)}")

    return []

def save_video(video_url: str, save_dir: str = "") -> str:
    if not save_dir:
        save_dir = utils.storage_dir("cache_videos")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    url_without_query = video_url.split("?")[0]
    url_hash = utils.md5(url_without_query)
    video_id = f"vid-{url_hash}"
    video_path = f"{save_dir}/{video_id}.mp4"

    # if video already exists, return the path
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"video already exists: {video_path}")
        return video_path

    # if video does not exist, download it
    proxies = config.pexels.get("proxies", None)
    with open(video_path, "wb") as f:
        f.write(requests.get(video_url, proxies=proxies, verify=False, timeout=(60, 240)).content)

    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        return video_path
    return ""


def download_videos(task_id: str,
                    search_terms: List[VideoParagraph],
                    video_aspect: VideoAspect = VideoAspect.portrait,
                    video_contact_mode: VideoConcatMode = VideoConcatMode.random,
                    audio_duration: float = 0.0,
                    max_clip_duration: int = 5,
                    ) -> List[str]:
    valid_video_items = []
    valid_video_urls = []
    found_duration = 0.0
    for search_term in search_terms:
        # logger.info(f"searching videos for '{search_term}'")
        duration = search_term.duration if search_term.duration > 0 else  max_clip_duration
        video_items = search_videos(search_term=search_term.text,
                                    duration=duration,
                                    video_aspect=video_aspect)
        logger.info(f"found {len(video_items)} videos for '{search_term.text}'")

        for item in video_items:
            if item.url not in valid_video_urls:
                valid_video_items.append(item)
                valid_video_urls.append(item.url)
                found_duration += item.duration

    logger.info(
        f"found total videos: {len(valid_video_items)}, required duration: {audio_duration} seconds, found duration: {found_duration} seconds")
    video_paths = []

    material_directory = config.app.get("material_directory", "").strip()
    if material_directory == "task":
        material_directory = utils.task_dir(task_id)
    elif material_directory and not os.path.isdir(material_directory):
        material_directory = ""

    if video_contact_mode.value == VideoConcatMode.random.value:
        random.shuffle(valid_video_items)

    total_duration = 0.0
    for item in valid_video_items:
        try:
            logger.info(f"downloading video: {item.url}")
            saved_video_path = save_video(video_url=item.url, save_dir=material_directory)
            if saved_video_path:
                logger.info(f"video saved: {saved_video_path}")
                video_paths.append(saved_video_path)
                seconds = min(max_clip_duration, item.duration)
                total_duration += seconds
                if total_duration > audio_duration:
                    logger.info(f"total duration of downloaded videos: {total_duration} seconds, skip downloading more")
                    break
        except Exception as e:
            logger.error(f"failed to download video: {utils.to_json(item)} => {str(e)}")
    logger.success(f"downloaded {len(video_paths)} videos")
    return video_paths


if __name__ == "__main__":
    download_videos("test1232", [
        "北京的春天生机勃勃",
        "有许多好玩的地方",
        "可以去颐和园赏花踏青",
        "漫步在长廊中",
        "欣赏湖光山色",
        "还可以去天坛公园放风筝",
        "在广阔的广场上奔跑嬉戏",
        "如果喜欢历史文化",
        "可以去故宫博物院参观",
        "了解中国古代的辉煌历史"
    ], audio_duration=21, max_clip_duration=15)

# If you could not download the model from the official site, you can use the mirror site.
# Just remove the comment of the following line .
# 如果你无法从官方网站下载模型，你可以使用镜像网站。
# 只需要移除下面一行的注释即可。

# export HF_ENDPOINT=https://hf-mirror.com
  ports=(8501 8502 8503 8504)
  for port in "${ports[@]}"; do
      for ((i=0; i<6; i++)); do
          pid=$(lsof -i :$port | awk 'NR==2 {print $2}')
          if [ -n "$pid" ]; then
              echo "端口 $port 被 $pid 占用. 尝试重新启动..."
              lsof -i :$port | awk 'NR==2 {print $2}' | xargs kill -9
              sleep 2
          else
              break
          fi
      done
  done
streamlit run ./webui/Main.py --browser.serverAddress="0.0.0.0" --server.enableCORS=True --browser.gatherUsageStats=False
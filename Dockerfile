# KLİPLİNK sunucusu (Render.com / herhangi bir Docker sunucusu için)
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core fonts-noto-color-emoji fonts-inter \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir flask gunicorn opencv-python-headless pillow numpy
COPY kliplink /app/kliplink
COPY .claude/skills/stream-clips/scripts/sc /app/.claude/skills/stream-clips/scripts/sc
RUN mkdir -p /app/kliplink/models && python -c "import urllib.request;urllib.request.urlretrieve('https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx','/app/kliplink/models/face_yunet.onnx')"
WORKDIR /app/kliplink
ENV PORT=10000 OUT_W=720
CMD gunicorn -w 1 --threads 8 --timeout 900 -b 0.0.0.0:$PORT app:app

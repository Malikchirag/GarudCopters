# python:3.10-slim: Ultralytics/torch wheels are well-tested against 3.10,
# and slim keeps the base image small since we don't need the full Debian
# toolchain -- opencv-python-headless-style system deps are added explicitly
# below rather than pulled in by a bigger base image.
FROM python:3.10-slim

WORKDIR /app

# libgl1/libglib2.0-0: opencv-python needs these even for headless
# image/video decoding (cv2 links against them at import time) -- without
# them the container builds fine but crashes on the first `import cv2`.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY inference.py train.py ./
COPY models/ ./models/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

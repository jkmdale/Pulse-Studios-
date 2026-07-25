FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y gcc g++ libsndfile1-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
# ffmpeg binary (required by ffmpeg-python wrapper)
# libsndfile1 (required by soundfile at runtime — dynamic link, not just build-time)
RUN apt-get update && apt-get install -y ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY backend/ .
COPY assets/ ./assets/
COPY web/ ./web/

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

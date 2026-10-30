FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SHOW_DATA_DIR=/data/jobs FFMPEG_PATH=/usr/bin/ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt
RUN groupadd --gid 10001 studio && useradd --uid 10001 --gid studio --no-create-home studio && mkdir -p /data/jobs && chown -R studio:studio /data
COPY scripts ./scripts
COPY webapp ./webapp
COPY run_studio.py .
USER studio
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["python", "run_studio.py", "--host", "0.0.0.0", "--port", "8080"]

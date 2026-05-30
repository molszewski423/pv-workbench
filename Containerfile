FROM python:3.11-slim

# discord.py[voice] needs opus/sodium; faster-whisper needs ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopus0 libsodium23 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY vault/ ./vault/

# Placeholder dirs — production paths are volume-mounted over these
RUN mkdir -p chroma_db output .streamlit .local_config

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_BASE_URL=http://ollama:11434

EXPOSE 8501

# Default: Streamlit dashboard. Override command: for the bot container.
CMD ["streamlit", "run", "src/dashboard/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true"]

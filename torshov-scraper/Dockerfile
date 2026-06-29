FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libevent-2.1-7 \
    libexpat1 \
    libffi8 \
    libgcc-s1 \
    libstdc++6 \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright==1.60.0

RUN python -m playwright install chromium

RUN python -m playwright install-deps chromium || true

WORKDIR /app

COPY scraper.py /app/
COPY run.sh /run.sh
RUN chmod +x /run.sh

ENV STATE_FILE=/data/state.json
ENV LOG_FILE=/data/scraper.log

CMD ["/run.sh"]

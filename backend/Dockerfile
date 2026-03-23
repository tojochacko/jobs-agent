FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Playwright/Chromium requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    chromium \
    chromium-driver \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/usr/lib/chromium
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Build context is the project root, so requirements.txt is at backend/requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend package so imports like `from backend.xxx` resolve correctly
COPY backend/ ./backend/

# Ensure persistent data directories exist
RUN mkdir -p /app/uploads /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

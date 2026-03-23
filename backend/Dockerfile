FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (Playwright will need more in Phase 2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Build context is the project root, so requirements.txt is at backend/requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend package so imports like `from backend.xxx` resolve correctly
COPY backend/ ./backend/

# Ensure persistent data directories exist
RUN mkdir -p /app/uploads /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

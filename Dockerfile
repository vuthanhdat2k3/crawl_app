# ==================== Manga Heaven - Dockerfile ====================
# Deploy on Railway - Cloud Only Mode

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN pip install playwright && playwright install chromium

# Copy application code
COPY . .

# Create directories
RUN mkdir -p crawler/browser_profile

# Environment
ENV PYTHONUNBUFFERED=1

# Use shell form - this ensures variable expansion works
CMD sh -c "gunicorn --bind 0.0.0.0:\${PORT:-5000} --workers 2 --timeout 120 web.app:app"

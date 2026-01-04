# ==================== Manga Heaven - Dockerfile ====================
# Deploy on Railway - Cloud Only Mode
# Uses MongoDB Atlas + ImageKit.io

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

# Make entrypoint executable and convert to Unix line endings
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Environment
ENV PYTHONUNBUFFERED=1

# Railway injects PORT automatically - just run the entrypoint
CMD ["./entrypoint.sh"]

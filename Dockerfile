# ==================== Manga Heaven - Dockerfile ====================
# Deploy on Railway, Render, or any Docker platform
# Uses MongoDB Atlas + ImageKit.io Cloud Storage

FROM python:3.11-slim

# Set working directory
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

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN pip install playwright && playwright install chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p crawler/browser_profile

# Set environment variables (override with Railway env vars)
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production

# Expose port (not strictly necessary for Railway but good practice)
EXPOSE $PORT

# Health check - tăng timeout để app kịp khởi động
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-5000}/ || exit 1

# Run the application with gunicorn
# Railway tự động inject biến PORT
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 web.app:app

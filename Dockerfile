# Use Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    ghostscript \
    libsm6 \
    libxext6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 2. Fix ImageMagick Policy (The Smart Way)
# Finds the policy.xml file wherever it is installed and modifies it
RUN find /etc -name "policy.xml" -exec sed -i 's/none/read,write/g' {} +

# 3. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Code
COPY . .

# Create necessary directories
RUN mkdir -p jobs assets/fonts assets/backgrounds

# 5. Set Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
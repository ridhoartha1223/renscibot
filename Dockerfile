# Gunakan Python 3.11
FROM python:3.11-slim

# Install dependencies untuk Node.js & npm
RUN apt-get update && \
    apt-get install -y curl build-essential gnupg ca-certificates python3 && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g lottie2tgs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project
COPY requirements.txt .
COPY main.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set default environment variables (Railway akan override)
ENV API_ID=0
ENV API_HASH=YOUR_API_HASH
ENV BOT_TOKEN=YOUR_BOT_TOKEN

# Jalankan bot
CMD ["python", "main.py"]

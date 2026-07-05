FROM python:3.10-slim

WORKDIR /app

# Install system dependency packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 8080 (standard for Cloud Run)
EXPOSE 8080

# Run FastAPI using uvicorn mapping the Cloud Run PORT environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p uploads temp

# Expose port (Cloud Run uses PORT env var, default 8080)
EXPOSE 8080

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run the application using shell form to expand $PORT
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app

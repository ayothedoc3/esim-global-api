FROM python:3.9-slim

WORKDIR /app

# Set Python to run in unbuffered mode for better log output in Cloud Run
ENV PYTHONUNBUFFERED=1

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (exclude unnecessary files)
COPY main.py ./
COPY routes/ ./routes/
COPY models/ ./models/
COPY services/ ./services/
COPY utils/ ./utils/
COPY static/ ./static/

# Default environment variables
ENV WORDPRESS_PRIMARY_SOURCE=true \
    DEBUG_MODE=true \
    ALLOW_SAMPLE_DATA_FALLBACK=true \
    LISTEN_PORT=8080 \
    LISTEN_HOST=0.0.0.0 \
    # Set recommended environment variables for containers
    PORT=8080

# Expose the port the app runs on
EXPOSE 8080

# Use a non-root user for better security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Command to run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} 
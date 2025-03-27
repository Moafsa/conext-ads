# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt requirements-test.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt -r requirements-test.txt

# Copy source code and tests
COPY src/ src/
COPY tests/ tests/
COPY config/ config/

# Create directories for models and data
RUN mkdir -p models tests/data templates/compliance

# Set environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=test

# Command to run tests
CMD ["pytest", "tests/", "-v", "--cov=src"]
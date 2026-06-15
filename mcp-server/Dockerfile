FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for python-docx and pdf processing
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create templates directory (templates can be mounted via volume)
RUN mkdir -p /app/templates

EXPOSE 5000

CMD ["python", "server.py"]
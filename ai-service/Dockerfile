# AI Service Dockerfile - Python FastAPI
FROM python:3.11-slim

WORKDIR /app

# Install uv for dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Generate uv.lock if it doesn't exist and install dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY main.py ./
COPY agent/ ./agent/
COPY api/ ./api/
COPY core/ ./core/
COPY services/ ./services/

# Expose port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3001/health')"

# Start server with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3001", "--reload"]
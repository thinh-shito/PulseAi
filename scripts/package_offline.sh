#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== 1. Building Production Docker Images ==="
docker compose -f docker-compose.prod.yml build

echo "=== 2. Exporting and Compressing Images to Tarball ==="
# Pull the third-party images first to ensure they are available locally
docker pull postgres:16-alpine
docker pull redis:7-alpine

# Save images to tar and gzip them
docker save \
  postgres:16-alpine \
  redis:7-alpine \
  pulseai-backend:latest \
  pulseai-frontend:latest \
  | gzip > pulseai-release.tar.gz


echo "=== 3. Creating Deployment Directory ==="
TEMP_DIR="pulseai-deployment-temp"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Copy package contents
mv pulseai-release.tar.gz "$TEMP_DIR/"
cp docker-compose.prod.yml "$TEMP_DIR/docker-compose.yml"
cp .env.example "$TEMP_DIR/.env"
cp scripts/seed_dev.py "$TEMP_DIR/seed_dev.py"

# Create a self-contained installation script for the client server
cat << 'EOF' > "$TEMP_DIR/deploy.sh"
#!/bin/bash
set -e

# Navigate to the directory where this script is located
cd "$(dirname "$0")"

echo "=== Deploying PulseAI Offline ==="

# Check if docker is installed
if ! [ -x "$(command -v docker)" ]; then
  echo "Error: docker is not installed. Please install Docker first." >&2
  exit 1
fi

if ! [ -x "$(command -v docker-compose)" ] && ! docker compose version &> /dev/null; then
  echo "Error: docker-compose/docker compose is not installed. Please install Docker Compose first." >&2
  exit 1
fi

echo "1. Loading offline Docker Images..."
docker load -i pulseai-release.tar.gz

echo "2. Copying environment configuration..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env file. Please edit it to configure secrets if needed."
else
  echo ".env file already exists. Skipping copy."
fi

echo "3. Starting PulseAI services..."
docker compose up -d

echo "Waiting 5 seconds for PostgreSQL database to be ready..."
sleep 5

echo "4. Running database migrations..."
docker compose exec -T backend alembic upgrade head

echo "5. Seeding default clinical accounts..."
docker cp seed_dev.py pulseai-backend:/app/seed_dev.py
docker compose exec -T backend python /app/seed_dev.py
docker compose exec -T backend rm /app/seed_dev.py

echo "=== Deployment successful! ==="
echo "Frontend is running on: http://localhost:3000"
echo "Backend API is running on: http://localhost:8000"
EOF

chmod +x "$TEMP_DIR/deploy.sh"

echo "=== 4. Archiving to single deployment ZIP file ==="
cd "$TEMP_DIR"
zip -r ../pulseai-deployment.zip . -x "*.DS_Store"
cd ..

# Clean up temporary directory
rm -rf "$TEMP_DIR"

echo "=============================================="
echo " Packaging completed successfully!"
echo " Output file: pulseai-deployment.zip"
echo "=============================================="

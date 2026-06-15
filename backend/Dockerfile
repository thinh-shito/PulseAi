# Development Dockerfile for NestJS Backend
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./
COPY nest-cli.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Start development server with hot reload
CMD ["npm", "run", "start:dev"]
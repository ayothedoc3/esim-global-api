# eSIM Global - Docker Build and Run Script for Windows
# This script builds and runs the FastAPI application in Docker

# Colors for terminal output
function Write-Color {
    param (
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "===============================================" -Color Cyan
Write-Color "   eSIM Global FastAPI Docker Deployment       " -Color Cyan
Write-Color "===============================================" -Color Cyan
Write-Color ""

Write-Color "This script will build and run your FastAPI application in Docker." -Color Yellow
Write-Color ""

# Check if Docker is installed
Write-Color "Checking for Docker..." -Color Yellow
$dockerVersion = docker --version 2>&1
if (-not $?) {
    Write-Color "❌ Docker not found! Please install Docker Desktop." -Color Red
    Write-Color "Download from: https://www.docker.com/products/docker-desktop" -Color Yellow
    exit 1
} else {
    Write-Color "✅ Found $dockerVersion" -Color Green
}

# Check for .env file
Write-Color "Checking for .env file..." -Color Yellow
if (-not (Test-Path -Path ".env")) {
    if (Test-Path -Path ".env.example") {
        Copy-Item ".env.example" -Destination ".env"
        Write-Color "✅ Created .env file from .env.example" -Color Green
    } else {
        Write-Color "⚠️ .env.example not found! Creating a basic .env file." -Color Yellow
        @"
# WordPress Configuration (Primary Data Source)
WORDPRESS_URL=https://wordpress-1368009-5111398.cloudwaysapps.com
WORDPRESS_APP_USERNAME=rana1
WORDPRESS_APP_PASSWORD=TSQJ TqlX aI1y waL0 VxK0 eHoO
WORDPRESS_PRIMARY_SOURCE=true

# FastAPI Configuration
FASTAPI_API_KEY=simtlvapikeyfortesting123
DEBUG_MODE=true
REFRESH_INTERVAL=300
LISTEN_PORT=8080
LISTEN_HOST=0.0.0.0

# Fallback Configuration
ALLOW_SAMPLE_DATA_FALLBACK=true
"@ | Out-File -FilePath ".env" -Encoding utf8
        Write-Color "✅ Created basic .env file" -Color Green
    }
} else {
    Write-Color "✅ .env file already exists" -Color Green
}

# Build the Docker image
Write-Color "Building Docker image..." -Color Yellow
docker build -t esim-global-api .
if (-not $?) {
    Write-Color "❌ Failed to build Docker image." -Color Red
    exit 1
}
Write-Color "✅ Docker image built successfully" -Color Green

# Check if the container is already running
$containerId = docker ps -q --filter "name=esim-global-api"
if ($containerId) {
    Write-Color "Found running container with ID: $containerId" -Color Yellow
    Write-Color "Stopping existing container..." -Color Yellow
    docker stop esim-global-api
    docker rm esim-global-api
    Write-Color "✅ Stopped and removed existing container" -Color Green
}

# Run the Docker container
Write-Color "Starting Docker container..." -Color Yellow
docker run -d --name esim-global-api -p 8080:8080 --env-file .env esim-global-api
if (-not $?) {
    Write-Color "❌ Failed to start Docker container." -Color Red
    exit 1
}
Write-Color "✅ Docker container started successfully" -Color Green

# Show logs
Write-Color "Container is now running. Showing logs:" -Color Yellow
Write-Color "Press Ctrl+C to stop watching logs (the container will continue running)" -Color Yellow
docker logs -f esim-global-api

# After logs are stopped, show the URLs
Write-Color ""
Write-Color "The application is available at:" -Color Green
Write-Color "http://localhost:8080" -Color Cyan
Write-Color "API Documentation available at:" -Color Green
Write-Color "http://localhost:8080/docs" -Color Cyan
Write-Color ""
Write-Color "To stop the container, run: docker stop esim-global-api" -Color Yellow 
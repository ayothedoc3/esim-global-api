# eSIM Global - Google Cloud Run Deployment Script (PowerShell)
# This script deploys the FastAPI application to Google Cloud Run

# Default configuration - MODIFY THESE VALUES
$GCP_PROJECT = "gen-lang-client-0142087325"  # Your Google Cloud Project ID
$SERVICE_NAME = "simtlv-api"                 # Service name for Cloud Run
$REGION = "us-central1"                      # GCP region
$MAX_INSTANCES = "10"                        # Maximum number of instances
$MIN_INSTANCES = "0"                         # Minimum number of instances
$MEMORY = "256Mi"                            # Memory allocation
$CPU = "1"                                   # CPU allocation
$TIMEOUT = "300s"                            # Request timeout
$CONCURRENCY = "80"                          # Concurrent requests per instance
$PORT = "8080"                               # Container port

# Function for colored output
function Write-Color {
    param (
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

# Print header
Write-Color "===============================================" -Color Cyan
Write-Color "   eSIM Global Google Cloud Run Deployment     " -Color Cyan
Write-Color "===============================================" -Color Cyan
Write-Color ""

# Function to check prerequisites
function Check-Prerequisites {
    Write-Color "Checking prerequisites..." -Color Yellow
    
    # Check if Google Cloud SDK is installed
    if (!(Get-Command gcloud -ErrorAction SilentlyContinue)) {
        Write-Color "❌ Google Cloud SDK (gcloud) is not installed" -Color Red
        Write-Color "Please install it from: https://cloud.google.com/sdk/docs/install" -Color Yellow
        return $false
    }
    
    # Check if Docker is installed
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Color "❌ Docker is not installed" -Color Red
        Write-Color "Please install Docker from: https://docs.docker.com/get-docker/" -Color Yellow
        return $false
    }
    
    # Check if user is logged in to gcloud
    try {
        $null = gcloud auth print-access-token
    } catch {
        Write-Color "❌ Not logged in to Google Cloud" -Color Red
        Write-Color "Please run: gcloud auth login" -Color Yellow
        return $false
    }
    
    # Check if Docker is running
    try {
        $null = docker info
    } catch {
        Write-Color "❌ Docker is not running" -Color Red
        Write-Color "Please start Docker and try again" -Color Yellow
        return $false
    }
    
    Write-Color "✅ All prerequisites satisfied" -Color Green
    return $true
}

# Function to set up GCP project
function Setup-GCPProject {
    Write-Color "Setting up Google Cloud Project..." -Color Yellow
    
    # Set the project
    gcloud config set project $GCP_PROJECT
    
    # Enable required APIs
    gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
    
    Write-Color "✅ GCP project setup complete" -Color Green
}

# Function to build and push Docker image
function Build-And-PushImage {
    Write-Color "Building and pushing Docker image..." -Color Yellow
    
    # Navigate to the directory with Dockerfile
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptDir
    
    # Check if Dockerfile exists
    if (!(Test-Path "Dockerfile")) {
        Write-Color "❌ Dockerfile not found in current directory" -Color Red
        return $null
    }
    
    # Set image name
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $imageName = "gcr.io/$GCP_PROJECT/$SERVICE_NAME`:$timestamp"
    
    # Build the image
    Write-Color "Building Docker image..." -Color Yellow
    docker build -t $imageName .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Color "❌ Docker build failed" -Color Red
        return $null
    }
    
    # Push the image to Google Container Registry
    Write-Color "Pushing image to Google Container Registry..." -Color Yellow
    docker push $imageName
    
    if ($LASTEXITCODE -ne 0) {
        Write-Color "❌ Failed to push Docker image" -Color Red
        return $null
    }
    
    Write-Color "✅ Image built and pushed successfully: $imageName" -Color Green
    return $imageName
}

# Function to deploy to Cloud Run
function Deploy-ToCloudRun {
    param (
        [string]$ImageName
    )
    
    Write-Color "Deploying to Google Cloud Run..." -Color Yellow
    
    # Check if we have an image name
    if ([string]::IsNullOrEmpty($ImageName)) {
        Write-Color "❌ No image name provided for deployment" -Color Red
        return $false
    }
    
    # Deploy to Cloud Run with optimized settings
    Write-Color "Creating/updating Cloud Run service..." -Color Yellow
    
    gcloud run deploy $SERVICE_NAME `
        --image=$ImageName `
        --platform=managed `
        --region=$REGION `
        --max-instances=$MAX_INSTANCES `
        --min-instances=$MIN_INSTANCES `
        --memory=$MEMORY `
        --cpu=$CPU `
        --timeout=$TIMEOUT `
        --concurrency=$CONCURRENCY `
        --port=$PORT `
        --allow-unauthenticated
    
    if ($LASTEXITCODE -ne 0) {
        Write-Color "❌ Deployment to Cloud Run failed" -Color Red
        return $false
    }
    
    Write-Color "✅ Deployment to Cloud Run successful" -Color Green
    return $true
}

# Function to clean up old resources
function Clean-Up {
    Write-Color "Cleaning up old resources..." -Color Yellow
    
    # List all revisions
    $revisions = gcloud run revisions list --service=$SERVICE_NAME --platform=managed --region=$REGION --format="value(metadata.name)"
    $revisionArray = $revisions -split "`n" | Where-Object { $_ -ne "" }
    
    # Keep only the latest 3 revisions
    if ($revisionArray.Count -gt 3) {
        Write-Color "Found $($revisionArray.Count) revisions, keeping the latest 3" -Color Yellow
        
        # Sort revisions (they are typically already sorted by name, which includes timestamp)
        $sortedRevisions = $revisionArray | Sort-Object
        
        # Delete older revisions
        for ($i = 0; $i -lt $sortedRevisions.Count - 3; $i++) {
            $rev = $sortedRevisions[$i]
            Write-Color "Deleting old revision: $rev" -Color Yellow
            gcloud run revisions delete $rev --quiet --platform=managed --region=$REGION
        }
    } else {
        Write-Color "Only $($revisionArray.Count) revisions found, no cleanup needed" -Color Yellow
    }
    
    Write-Color "✅ Cleanup completed" -Color Green
}

# Function to check deployment
function Check-Deployment {
    Write-Color "Checking deployment..." -Color Yellow
    
    # Get the URL of the deployed service
    $url = gcloud run services describe $SERVICE_NAME --platform=managed --region=$REGION --format="value(status.url)"
    
    if ([string]::IsNullOrEmpty($url)) {
        Write-Color "❌ Could not get service URL" -Color Red
        return $false
    }
    
    # Check if the service is responding
    Write-Color "Checking if service is responding at $url" -Color Yellow
    
    try {
        $response = Invoke-WebRequest -Uri "$url/api/health" -UseBasicParsing
        $content = $response.Content
        
        if ($content -match "status.*ok") {
            Write-Color "✅ Service is responding correctly" -Color Green
            
            Write-Color "===============================================" -Color Cyan
            Write-Color "Deployment completed successfully!" -Color Green
            Write-Color "Your API is now accessible at:" -Color Cyan
            Write-Host $url
            Write-Color "API Documentation:" -Color Cyan
            Write-Host "$url/docs"
            Write-Color "Health Check:" -Color Cyan
            Write-Host "$url/api/health"
            Write-Color "===============================================" -Color Cyan
            return $true
        } else {
            Write-Color "❌ Service is not responding correctly" -Color Red
            Write-Color "Check logs with: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME'" -Color Yellow
            return $false
        }
    } catch {
        Write-Color "❌ Failed to connect to service: $_" -Color Red
        Write-Color "Check logs with: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME'" -Color Yellow
        return $false
    }
}

# Main deployment workflow
function Main {
    if (!(Check-Prerequisites)) {
        Write-Color "❌ Prerequisites check failed" -Color Red
        exit 1
    }
    
    Setup-GCPProject
    
    $imageName = Build-And-PushImage
    if ([string]::IsNullOrEmpty($imageName)) {
        Write-Color "❌ Failed to build and push image" -Color Red
        exit 1
    }
    
    if (!(Deploy-ToCloudRun -ImageName $imageName)) {
        Write-Color "❌ Deployment failed" -Color Red
        exit 1
    }
    
    Clean-Up
    
    if (!(Check-Deployment)) {
        Write-Color "❌ Deployment verification failed" -Color Red
        exit 1
    }
    
    Write-Color "✅ Deployment workflow completed successfully!" -Color Green
}

# Run the main function
Main 
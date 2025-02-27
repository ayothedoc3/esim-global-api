#!/bin/bash
# eSIM Global - Google Cloud Run Deployment Script
# This script deploys the FastAPI application to Google Cloud Run

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration - MODIFY THESE VALUES
GCP_PROJECT="gen-lang-client-0142087325"  # Your Google Cloud Project ID
SERVICE_NAME="simtlv-api"                 # Service name for Cloud Run
REGION="us-central1"                      # GCP region
MAX_INSTANCES="10"                        # Maximum number of instances
MIN_INSTANCES="0"                         # Minimum number of instances
MEMORY="256Mi"                            # Memory allocation
CPU="1"                                   # CPU allocation
TIMEOUT="300s"                            # Request timeout
CONCURRENCY="80"                          # Concurrent requests per instance
PORT="8080"                               # Container port

# Print header
echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}   eSIM Global Google Cloud Run Deployment     ${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_message "$YELLOW" "Checking prerequisites..."
    
    # Check if Google Cloud SDK is installed
    if ! command -v gcloud &> /dev/null; then
        print_message "$RED" "❌ Google Cloud SDK (gcloud) is not installed"
        print_message "$YELLOW" "Please install it from: https://cloud.google.com/sdk/docs/install"
        return 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_message "$RED" "❌ Docker is not installed"
        print_message "$YELLOW" "Please install Docker from: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    # Check if user is logged in to gcloud
    if ! gcloud auth print-access-token &> /dev/null; then
        print_message "$RED" "❌ Not logged in to Google Cloud"
        print_message "$YELLOW" "Please run: gcloud auth login"
        return 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_message "$RED" "❌ Docker is not running"
        print_message "$YELLOW" "Please start Docker and try again"
        return 1
    fi
    
    print_message "$GREEN" "✅ All prerequisites satisfied"
    return 0
}

# Function to set up GCP project
setup_gcp_project() {
    print_message "$YELLOW" "Setting up Google Cloud Project..."
    
    # Set the project
    gcloud config set project "$GCP_PROJECT"
    
    # Enable required APIs
    gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
    
    print_message "$GREEN" "✅ GCP project setup complete"
}

# Function to build and push Docker image
build_and_push_image() {
    print_message "$YELLOW" "Building and pushing Docker image..."
    
    # Navigate to the directory with Dockerfile
    cd "$(dirname "$0")" || { print_message "$RED" "❌ Could not find application directory"; return 1; }
    
    # Check if Dockerfile exists
    if [ ! -f "Dockerfile" ]; then
        print_message "$RED" "❌ Dockerfile not found in current directory"
        return 1
    fi
    
    # Set image name
    local timestamp=$(date +%Y%m%d%H%M%S)
    local image_name="gcr.io/$GCP_PROJECT/$SERVICE_NAME:$timestamp"
    
    # Build the image
    print_message "$YELLOW" "Building Docker image..."
    if ! docker build -t "$image_name" .; then
        print_message "$RED" "❌ Docker build failed"
        return 1
    fi
    
    # Push the image to Google Container Registry
    print_message "$YELLOW" "Pushing image to Google Container Registry..."
    if ! docker push "$image_name"; then
        print_message "$RED" "❌ Failed to push Docker image"
        return 1
    fi
    
    print_message "$GREEN" "✅ Image built and pushed successfully: $image_name"
    echo "$image_name"  # Return the image name for later use
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
    local image_name=$1
    
    print_message "$YELLOW" "Deploying to Google Cloud Run..."
    
    # Check if we have an image name
    if [ -z "$image_name" ]; then
        print_message "$RED" "❌ No image name provided for deployment"
        return 1
    fi
    
    # Deploy to Cloud Run with optimized settings
    print_message "$YELLOW" "Creating/updating Cloud Run service..."
    
    if ! gcloud run deploy "$SERVICE_NAME" \
        --image="$image_name" \
        --platform=managed \
        --region="$REGION" \
        --max-instances="$MAX_INSTANCES" \
        --min-instances="$MIN_INSTANCES" \
        --memory="$MEMORY" \
        --cpu="$CPU" \
        --timeout="$TIMEOUT" \
        --concurrency="$CONCURRENCY" \
        --port="$PORT" \
        --allow-unauthenticated; then
        print_message "$RED" "❌ Deployment to Cloud Run failed"
        return 1
    fi
    
    print_message "$GREEN" "✅ Deployment to Cloud Run successful"
    return 0
}

# Function to clean up old resources
clean_up() {
    print_message "$YELLOW" "Cleaning up old resources..."
    
    # List all revisions
    local revisions=($(gcloud run revisions list --service="$SERVICE_NAME" --platform=managed --region="$REGION" --format="value(metadata.name)"))
    
    # Keep only the latest 3 revisions
    if [ ${#revisions[@]} -gt 3 ]; then
        print_message "$YELLOW" "Found ${#revisions[@]} revisions, keeping the latest 3"
        
        # Sort revisions (they are typically already sorted by name, which includes timestamp)
        IFS=$'\n' sorted_revisions=($(sort <<<"${revisions[*]}"))
        unset IFS
        
        # Delete older revisions
        for (( i=0; i<${#sorted_revisions[@]}-3; i++ )); do
            local rev="${sorted_revisions[$i]}"
            print_message "$YELLOW" "Deleting old revision: $rev"
            gcloud run revisions delete "$rev" --quiet --platform=managed --region="$REGION"
        done
    else
        print_message "$YELLOW" "Only ${#revisions[@]} revisions found, no cleanup needed"
    fi
    
    print_message "$GREEN" "✅ Cleanup completed"
}

# Function to check deployment
check_deployment() {
    print_message "$YELLOW" "Checking deployment..."
    
    # Get the URL of the deployed service
    local url=$(gcloud run services describe "$SERVICE_NAME" --platform=managed --region="$REGION" --format="value(status.url)")
    
    if [ -z "$url" ]; then
        print_message "$RED" "❌ Could not get service URL"
        return 1
    fi
    
    # Check if the service is responding
    print_message "$YELLOW" "Checking if service is responding at $url"
    
    if curl -s "$url/api/health" | grep -q "status.*ok"; then
        print_message "$GREEN" "✅ Service is responding correctly"
        
        print_message "$CYAN" "==============================================="
        print_message "$GREEN" "Deployment completed successfully!"
        print_message "$CYAN" "Your API is now accessible at:"
        echo "$url"
        print_message "$CYAN" "API Documentation:"
        echo "$url/docs"
        print_message "$CYAN" "Health Check:"
        echo "$url/api/health"
        print_message "$CYAN" "==============================================="
        return 0
    else
        print_message "$RED" "❌ Service is not responding correctly"
        print_message "$YELLOW" "Check logs with: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME'"
        return 1
    fi
}

# Main deployment workflow
main() {
    if ! check_prerequisites; then
        print_message "$RED" "❌ Prerequisites check failed"
        exit 1
    fi
    
    setup_gcp_project
    
    local image_name=$(build_and_push_image)
    if [ -z "$image_name" ]; then
        print_message "$RED" "❌ Failed to build and push image"
        exit 1
    fi
    
    if ! deploy_to_cloud_run "$image_name"; then
        print_message "$RED" "❌ Deployment failed"
        exit 1
    fi
    
    clean_up
    
    if ! check_deployment; then
        print_message "$RED" "❌ Deployment verification failed"
        exit 1
    fi
    
    print_message "$GREEN" "✅ Deployment workflow completed successfully!"
}

# Run the main function
main 
# Deploying eSIM Global API to Google Cloud Run

This guide provides instructions for deploying the eSIM Global FastAPI application to Google Cloud Run, a fully managed serverless platform.

## Why Google Cloud Run?

Google Cloud Run offers several advantages:

- **Serverless**: No need to provision, manage, or scale infrastructure
- **Fast Scaling**: Automatically scales to handle traffic spikes
- **Cost-Effective**: Pay only for what you use (compute time)
- **Container-Based**: Uses standard container technology
- **HTTPS**: Automatic HTTPS provisioning

## Prerequisites

Before you begin, make sure you have:

1. **Google Cloud Account**: Active Google Cloud account with billing enabled
2. **Google Cloud SDK**: Installed and configured on your machine
   - [Install Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. **Docker**: Installed and running on your machine
   - [Install Docker](https://docs.docker.com/get-docker/)
4. **Project Files**: Your FastAPI application files, including Dockerfile
5. **Google Cloud CLI authenticated**: Run `gcloud auth login` if not already authenticated

## Deployment Options

We provide two deployment scripts for convenience:

- **deploy_to_gcloud.sh**: For Linux/Mac users
- **deploy_to_gcloud.ps1**: For Windows users

Both scripts automate the entire deployment process, including:
- Building and pushing the Docker image
- Deploying to Google Cloud Run with optimized settings
- Setting up auto-scaling
- Cleaning up old revisions
- Verifying the deployment

## Configuration

Before running the deployment scripts, update the configuration variables at the top of the file to match your needs:

```bash
# For Linux/Mac
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
```

```powershell
# For Windows
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
```

## Deployment Instructions

### Option 1: Using Deployment Scripts

#### For Linux/Mac Users:

1. Make the script executable:
   ```bash
   chmod +x deploy_to_gcloud.sh
   ```

2. Run the script:
   ```bash
   ./deploy_to_gcloud.sh
   ```

#### For Windows Users:

1. Open PowerShell and navigate to your FastAPI application directory

2. Run the script:
   ```powershell
   .\deploy_to_gcloud.ps1
   ```

### Option 2: Manual Deployment

If you prefer to deploy manually:

1. **Build the Docker image**:
   ```bash
   docker build -t gcr.io/PROJECT_ID/simtlv-api:latest .
   ```

2. **Push the image to Google Container Registry**:
   ```bash
   docker push gcr.io/PROJECT_ID/simtlv-api:latest
   ```

3. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy simtlv-api \
      --image=gcr.io/PROJECT_ID/simtlv-api:latest \
      --platform=managed \
      --region=us-central1 \
      --memory=256Mi \
      --cpu=1 \
      --port=8080 \
      --allow-unauthenticated
   ```

## Environment Variables

When deploying to Google Cloud Run, you'll need to configure environment variables. You can do this:

1. **Via the Google Cloud Console**:
   - Go to Cloud Run > Your Service > Edit & Deploy New Revision
   - Under "Container, Networking, Security", expand "Container"
   - Add environment variables in the "Variables & Secrets" section

2. **Via gcloud CLI**:
   ```bash
   gcloud run services update simtlv-api \
     --update-env-vars="WORDPRESS_PRIMARY_SOURCE=true,DEBUG_MODE=true"
   ```

3. **In deployment scripts**:
   - The deployment scripts can be modified to include these variables

## Important Environment Variables

Make sure to set these environment variables for proper functionality:

```
WORDPRESS_URL=https://wordpress-1368009-5111398.cloudwaysapps.com
WORDPRESS_APP_USERNAME=rana1
WORDPRESS_APP_PASSWORD=TSQJ TqlX aI1y waL0 VxK0 eHoO
WORDPRESS_PRIMARY_SOURCE=true
FASTAPI_API_KEY=your_api_key_here
DEBUG_MODE=true
REFRESH_INTERVAL=300
LISTEN_PORT=8080
LISTEN_HOST=0.0.0.0
ALLOW_SAMPLE_DATA_FALLBACK=true
```

## Monitoring & Maintenance

### Viewing Logs

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=simtlv-api'
```

### Listing Revisions

```bash
gcloud run revisions list --service=simtlv-api --region=us-central1
```

### Cleaning Up Old Revisions

Our deployment scripts automatically retain only the latest 3 revisions to avoid accumulating unused resources. To manually clean up:

```bash
# List revisions
gcloud run revisions list --service=simtlv-api --region=us-central1

# Delete a specific revision
gcloud run revisions delete REVISION_NAME --region=us-central1
```

## Cost Optimization

Google Cloud Run offers a generous free tier and a pay-per-use model. To optimize costs:

1. **Instance Settings**:
   - Set minimum instances to 0 (default in our scripts)
   - Adjust maximum instances based on expected traffic

2. **Container Size**:
   - Use minimal base images (we use python:3.9-slim)
   - Set reasonable memory limits (default is 256Mi in our scripts)

3. **Concurrency**:
   - Higher concurrency values (default 80 in our scripts) reduce the number of instances needed

## Troubleshooting

### Common Issues

1. **Deployment Failed**:
   - Check Docker is running
   - Ensure Google Cloud APIs are enabled
   - Verify GCP project ID is correct

2. **API Not Responding**:
   - Check Cloud Run logs
   - Verify .env variables are properly set
   - Test the health endpoint: `/api/health`

3. **Container Crashes**:
   - Check logs for Python errors
   - Verify all dependencies are in requirements.txt
   - Test locally using the Dockerfile

### Getting Help

If you continue to encounter issues, you can:

1. Check Google Cloud Run documentation
2. Review Cloud Run logs for specific error messages
3. Verify network connectivity from Cloud Run to WordPress
4. Test with a minimal configuration to isolate issues

## Security Considerations

1. **API Key**: Protect your `FASTAPI_API_KEY` by setting it through Cloud Run environment variables
2. **WordPress Credentials**: Store these securely; consider using Secret Manager for production
3. **Public Access**: The deployment uses `--allow-unauthenticated` for public access; adjust if needed
4. **CORS Settings**: Configure `CORS_ORIGINS` appropriately for your frontend domains

## Next Steps

After successful deployment, you may want to:

1. Set up a custom domain for your API
2. Configure Cloud Run with a Cloud Armor security policy
3. Implement monitoring with Google Cloud Monitoring
4. Set up CI/CD for automatic deployments 
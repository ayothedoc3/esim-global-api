# Google Cloud Run Deployment Cleanup & Optimization

We've optimized the Google Cloud Run deployment for the eSIM Global FastAPI application to address the issues flagged by Google and improve overall reliability and security.

## Key Changes Made

### 1. Deployment Scripts
- Created two deployment scripts:
  - `deploy_to_gcloud.sh` (Bash) for Linux/Mac users
  - `deploy_to_gcloud.ps1` (PowerShell) for Windows users
- Both scripts handle the complete deployment workflow including:
  - Checking prerequisites
  - Building and pushing Docker images
  - Deploying to Cloud Run with optimized settings
  - Cleaning up old revisions
  - Verifying deployment success

### 2. Dockerfile Optimizations
- Added `PYTHONUNBUFFERED=1` for improved container logging
- Selective file copying to reduce container size
- Implemented security best practice of using a non-root user
- Used the Google-recommended `PORT` environment variable
- Improved CMD format to properly handle signals
- Set more explicit resource constraints

### 3. Resource Management
- Added automated cleanup of old revisions (keeping only the latest 3)
- Configured instance limits (min/max) for cost optimization
- Set memory and CPU allocations based on expected workload
- Configured concurrency settings for better scaling

### 4. Documentation
- Created comprehensive `GOOGLE_CLOUD_RUN.md` guide
- Added detailed instructions for:
  - Deployment options (automatic vs manual)
  - Environment variable configuration
  - Monitoring and maintenance
  - Troubleshooting common issues
  - Security best practices
  - Cost optimization strategies

### 5. Environment Variables
- Ensured all environment variables are properly set:
  - WordPress connection details
  - FastAPI configuration
  - Fallback options
  - Deployment-specific variables

## WordPress Integration Status

The API is fully configured to fetch live data from WordPress as the primary source:

1. **WordPress First Approach**: The system is set to try WordPress first, then fall back to TelcoVision only when necessary.

2. **ICCID Endpoint**: The `/api/iccid/{iccid}` endpoint will:
   - First attempt to get data from WordPress
   - Fall back to TelcoVision only if WordPress doesn't return valid data
   - Use sample data as a last resort (if enabled)

3. **Environment Configuration**: The necessary WordPress connection details are included in the deployment.

## Next Steps

1. **Run the deployment script** from the `fastapi-app` directory:
   - Linux/Mac: `./deploy_to_gcloud.sh`
   - Windows: `.\deploy_to_gcloud.ps1`

2. **Verify the deployment** by checking:
   - Health endpoint: `https://[your-cloud-run-url]/api/health`
   - API documentation: `https://[your-cloud-run-url]/docs`
   - ICCID endpoint: `https://[your-cloud-run-url]/api/iccid/[test-iccid]`

3. **Monitor logs** for any issues:
   ```bash
   gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=simtlv-api'
   ```

4. **Set custom domain** (optional) through the Google Cloud Console for a more professional API URL.

The optimized deployment should resolve any issues flagged by Google while maintaining full functionality with WordPress as the primary data source. 
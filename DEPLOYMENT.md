# eSIM Global FastAPI - Cloudways Deployment Guide

This guide walks you through the process of deploying the eSIM Global FastAPI application to a Cloudways server.

## Prerequisites

Before you begin, make sure you have:

1. **Cloudways Account and Server**: An active Cloudways account with a server running
2. **Server Access Information**:
   - Server IP address
   - SSH username (usually the same as the IP address)
   - SSH password
3. **Deployment Tools**:
   - **Windows**: PuTTY tools (plink, pscp) - [Download from putty.org](https://www.putty.org/)
   - **Linux/Mac**: OpenSSH client (typically pre-installed)
4. **FastAPI Application Code**: Your local copy of the eSIM Global FastAPI application

## Deployment Steps

### Step 1: Update Configuration

1. Navigate to your FastAPI application directory
2. Make sure your `.env` file is configured correctly with:
   - WordPress connection details
   - API keys
   - Other required environment variables

### Step 2: Run the Deployment Script

#### For Windows Users:

1. Open the `deploy_to_cloudways.ps1` file and update these variables at the top:
   ```powershell
   $SERVER_IP = "64.176.171.246"  # Your Cloudways server IP
   $SERVER_USERNAME = "your_username" # Usually same as IP address
   $SERVER_PASSWORD = "your_password" # Your SSH password
   $APP_NAME = "esim-api"  # Name for your application
   $APP_PATH = "/home/master/applications/$APP_NAME"  # Path on server
   ```

2. Open PowerShell and navigate to your FastAPI application directory
3. Run the script:
   ```powershell
   .\deploy_to_cloudways.ps1
   ```

#### For Linux/Mac Users:

1. Open the `deploy_to_cloudways.sh` file and update these variables at the top:
   ```bash
   SERVER_IP="64.176.171.246"  # Your Cloudways server IP
   SERVER_USERNAME="your_username" # Usually same as IP address
   SERVER_PASSWORD="your_password" # Your SSH password
   APP_NAME="esim-api"  # Name for your application
   APP_PATH="/home/master/applications/$APP_NAME"  # Path on server
   ```

2. Make the script executable:
   ```bash
   chmod +x deploy_to_cloudways.sh
   ```

3. Run the script:
   ```bash
   ./deploy_to_cloudways.sh
   ```

### Step 3: Verify Deployment

After the script completes successfully, you should see URLs for accessing your API:

- **API Endpoint**: `http://your-server-ip:8080`
- **API Documentation**: `http://your-server-ip:8080/docs`
- **Health Check**: `http://your-server-ip:8080/api/health`

Verify that your API is working by accessing these URLs in a web browser.

## Troubleshooting

If you encounter issues during deployment:

### Common Issues:

1. **Connection Failed**:
   - Verify your server IP, username, and password are correct
   - Check if you can SSH into the server manually
   - Ensure your server's firewall allows SSH connections

2. **Service Not Starting**:
   - Check logs on the server with: `sudo journalctl -u esim-api`
   - Verify Python is installed: `python3 --version`
   - Check if port 8080 is already in use: `sudo netstat -tulpn | grep 8080`

3. **API Not Responding**:
   - Verify the service is running: `sudo systemctl status esim-api`
   - Check app logs: `sudo journalctl -u esim-api -f`
   - Test with curl: `curl http://localhost:8080/api/health`

### Manual Deployment:

If the automated script fails, you can manually deploy with these steps:

1. SSH into your Cloudways server
2. Create the application directory: `mkdir -p /home/master/applications/esim-api/app`
3. Upload files using SCP or SFTP
4. Set up a Python virtual environment and install dependencies
5. Create and enable a systemd service

## Updating Your Deployment

To update your deployed application:

1. Make changes to your local application code
2. Run the deployment script again
3. The script will update files and restart the service

## Need Help?

If you continue to face deployment issues:
- Check the server's logs
- Ensure all environment variables are correctly set
- Contact Cloudways support if you suspect server configuration issues 
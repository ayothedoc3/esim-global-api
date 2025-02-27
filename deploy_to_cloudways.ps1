# eSIM Global - Cloudways Deployment Script
# This script deploys the FastAPI application to a Cloudways server

# Default values - REPLACE THESE with your actual values
$SERVER_IP = "64.176.171.246"  # Your Cloudways server IP
$SERVER_USERNAME = "your_username" # Usually same as IP address
$SERVER_PASSWORD = "your_password" # Your SSH password
$APP_NAME = "esim-api"  # Name for your application
$APP_PATH = "/home/master/applications/$APP_NAME"  # Path on server

# Colors for terminal output
function Write-Color {
    param (
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "===============================================" -Color Cyan
Write-Color "   eSIM Global FastAPI Cloudways Deployment    " -Color Cyan
Write-Color "===============================================" -Color Cyan
Write-Color ""

# Function to create a temporary SSH key for deployment
function Create-TempSSHKey {
    Write-Color "Creating temporary SSH key for deployment..." -Color Yellow
    
    # Create a temporary directory for the SSH key
    $sshKeyDir = "temp_ssh"
    if (!(Test-Path $sshKeyDir)) {
        New-Item -ItemType Directory -Path $sshKeyDir | Out-Null
    }
    
    # Generate a new SSH key
    $keyPath = "$sshKeyDir/id_rsa"
    if (Test-Path $keyPath) {
        Remove-Item $keyPath -Force
        Remove-Item "$keyPath.pub" -Force
    }
    
    try {
        # Try to create SSH key using ssh-keygen
        ssh-keygen -t rsa -b 2048 -f $keyPath -N '""' -q
        if ($LASTEXITCODE -ne 0) {
            throw "ssh-keygen failed with exit code $LASTEXITCODE"
        }
        Write-Color "✅ Temporary SSH key created" -Color Green
        return $keyPath
    }
    catch {
        Write-Color "❌ Failed to create SSH key: $_" -Color Red
        Write-Color "Continuing with password authentication..." -Color Yellow
        return $null
    }
}

# Function to create the application directory on the server
function Create-RemoteDirectory {
    Write-Color "Creating application directory on server..." -Color Yellow
    
    # Use plink to execute SSH commands
    $cmd = "mkdir -p $APP_PATH/app"
    
    # Run the command
    echo y | plink -ssh $SERVER_USERNAME@$SERVER_IP -pw $SERVER_PASSWORD $cmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Color "✅ Application directory created on server" -Color Green
        return $true
    }
    else {
        Write-Color "❌ Failed to create application directory on server" -Color Red
        return $false
    }
}

# Function to upload files to the server
function Upload-Files {
    Write-Color "Uploading application files to server..." -Color Yellow
    
    # Upload main application files
    $mainFiles = @(
        "main.py",
        "requirements.txt",
        ".env",
        "Dockerfile"
    )
    
    $successCount = 0
    
    foreach ($file in $mainFiles) {
        if (Test-Path $file) {
            Write-Color "Uploading $file..." -Color Yellow
            echo y | pscp -pw $SERVER_PASSWORD $file $SERVER_USERNAME@$SERVER_IP`:$APP_PATH/app/
            
            if ($LASTEXITCODE -eq 0) {
                Write-Color "✅ $file uploaded successfully" -Color Green
                $successCount++
            }
            else {
                Write-Color "❌ Failed to upload $file" -Color Red
            }
        }
        else {
            Write-Color "⚠️ $file not found in current directory" -Color Yellow
        }
    }
    
    # Create systemd service file
    $serviceContent = @"
[Unit]
Description=eSIM Global FastAPI Application
After=network.target

[Service]
User=master
WorkingDirectory=$APP_PATH/app
ExecStart=$APP_PATH/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10
Environment="PATH=$APP_PATH/venv/bin"

[Install]
WantedBy=multi-user.target
"@
    
    # Save service file locally
    $serviceContent | Out-File -FilePath "esim-api.service" -Encoding utf8
    
    # Upload service file
    echo y | pscp -pw $SERVER_PASSWORD "esim-api.service" $SERVER_USERNAME@$SERVER_IP`:$APP_PATH/
    
    if ($LASTEXITCODE -eq 0) {
        Write-Color "✅ Service file uploaded successfully" -Color Green
        $successCount++
    }
    else {
        Write-Color "❌ Failed to upload service file" -Color Red
    }
    
    # Remove local service file
    Remove-Item "esim-api.service" -Force
    
    return ($successCount -eq ($mainFiles.Count + 1))
}

# Function to set up the environment on the server
function Setup-Environment {
    Write-Color "Setting up environment on server..." -Color Yellow
    
    # Commands to set up the environment
    $setupCommands = @(
        "cd $APP_PATH",
        "# Install Python and pip if needed",
        "command -v python3 >/dev/null 2>&1 || { sudo apt-get update && sudo apt-get install -y python3 python3-pip; }",
        "# Create virtual environment",
        "python3 -m venv venv || python3 -m virtualenv venv",
        "# Install dependencies",
        "source venv/bin/activate && pip install -r app/requirements.txt",
        "# Copy service file to systemd directory",
        "sudo cp $APP_PATH/esim-api.service /etc/systemd/system/",
        "# Reload systemd and enable/start service",
        "sudo systemctl daemon-reload",
        "sudo systemctl enable esim-api",
        "sudo systemctl restart esim-api",
        "# Set up health check script",
        "echo '#!/bin/bash' > $APP_PATH/health_check.sh",
        "echo 'curl -s http://localhost:8080/api/health || sudo systemctl restart esim-api' >> $APP_PATH/health_check.sh",
        "chmod +x $APP_PATH/health_check.sh",
        "# Add health check to crontab",
        "(crontab -l 2>/dev/null; echo '*/5 * * * * $APP_PATH/health_check.sh') | crontab -"
    )
    
    # Create a script file with these commands
    $setupScript = $setupCommands -join "`n"
    $setupScript | Out-File -FilePath "setup.sh" -Encoding utf8
    
    # Upload the script
    echo y | pscp -pw $SERVER_PASSWORD "setup.sh" $SERVER_USERNAME@$SERVER_IP`:$APP_PATH/
    
    if ($LASTEXITCODE -ne 0) {
        Write-Color "❌ Failed to upload setup script" -Color Red
        Remove-Item "setup.sh" -Force
        return $false
    }
    
    # Execute the script
    echo y | plink -ssh $SERVER_USERNAME@$SERVER_IP -pw $SERVER_PASSWORD "chmod +x $APP_PATH/setup.sh && $APP_PATH/setup.sh"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Color "✅ Environment setup completed successfully" -Color Green
        Remove-Item "setup.sh" -Force
        return $true
    }
    else {
        Write-Color "❌ Failed to set up environment on server" -Color Red
        Remove-Item "setup.sh" -Force
        return $false
    }
}

# Function to verify deployment
function Verify-Deployment {
    Write-Color "Verifying deployment..." -Color Yellow
    
    # Check if the service is running
    echo y | plink -ssh $SERVER_USERNAME@$SERVER_IP -pw $SERVER_PASSWORD "sudo systemctl status esim-api | grep 'Active: active'"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Color "✅ Service is running" -Color Green
        
        # Check if the API is responding
        echo y | plink -ssh $SERVER_USERNAME@$SERVER_IP -pw $SERVER_PASSWORD "curl -s http://localhost:8080/api/health | grep 'status.*ok'"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Color "✅ API is responding correctly" -Color Green
            Write-Color "===============================================" -Color Cyan
            Write-Color "Deployment completed successfully!" -Color Green
            Write-Color "Your API is now accessible at:" -Color Cyan
            Write-Color "http://$SERVER_IP:8080" -Color White
            Write-Color "API Documentation: http://$SERVER_IP:8080/docs" -Color White
            Write-Color "===============================================" -Color Cyan
            return $true
        }
        else {
            Write-Color "❌ API is not responding correctly" -Color Red
            Write-Color "Please check logs with: sudo journalctl -u esim-api" -Color Yellow
            return $false
        }
    }
    else {
        Write-Color "❌ Service is not running" -Color Red
        Write-Color "Please check logs with: sudo journalctl -u esim-api" -Color Yellow
        return $false
    }
}

# Function to check if required tools are installed
function Check-Requirements {
    $tools = @("plink", "pscp")
    $missingTools = @()
    
    foreach ($tool in $tools) {
        if (!(Get-Command $tool -ErrorAction SilentlyContinue)) {
            $missingTools += $tool
        }
    }
    
    if ($missingTools.Count -gt 0) {
        Write-Color "❌ Missing required tools: $($missingTools -join ', ')" -Color Red
        Write-Color "Please install PuTTY tools from: https://www.putty.org/" -Color Yellow
        return $false
    }
    
    Write-Color "✅ All required tools are installed" -Color Green
    return $true
}

# Main deployment workflow
if (!(Check-Requirements)) {
    exit 1
}

Write-Color "Deploying to Cloudways server $SERVER_IP..." -Color Yellow

if (!(Create-RemoteDirectory)) {
    Write-Color "❌ Deployment failed: Could not create remote directory" -Color Red
    exit 1
}

if (!(Upload-Files)) {
    Write-Color "❌ Deployment failed: Could not upload all required files" -Color Red
    exit 1
}

if (!(Setup-Environment)) {
    Write-Color "❌ Deployment failed: Could not set up environment" -Color Red
    exit 1
}

if (!(Verify-Deployment)) {
    Write-Color "❌ Deployment verification failed" -Color Red
    exit 1
}

Write-Color "✅ Deployment completed successfully!" -Color Green 
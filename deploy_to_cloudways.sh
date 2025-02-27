#!/bin/bash
# eSIM Global - Cloudways Deployment Script (Bash version)
# This script deploys the FastAPI application to a Cloudways server

# Default values - REPLACE THESE with your actual values
SERVER_IP="64.176.171.246"  # Your Cloudways server IP
SERVER_USERNAME="your_username" # Usually same as IP address
SERVER_PASSWORD="your_password" # Your SSH password
APP_NAME="esim-api"  # Name for your application
APP_PATH="/home/master/applications/$APP_NAME"  # Path on server

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}   eSIM Global FastAPI Cloudways Deployment    ${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if required tools are installed
check_requirements() {
    print_message "$YELLOW" "Checking for required tools..."
    
    local missing_tools=()
    for tool in ssh scp; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=($tool)
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_message "$RED" "❌ Missing required tools: ${missing_tools[*]}"
        print_message "$YELLOW" "Please install OpenSSH client"
        return 1
    fi
    
    print_message "$GREEN" "✅ All required tools are installed"
    return 0
}

# Function to create the application directory on the server
create_remote_directory() {
    print_message "$YELLOW" "Creating application directory on server..."
    
    # Using sshpass if password is provided, otherwise normal SSH
    if ssh -o StrictHostKeyChecking=no -o BatchMode=yes "$SERVER_USERNAME@$SERVER_IP" "mkdir -p $APP_PATH/app"; then
        print_message "$GREEN" "✅ Application directory created on server"
        return 0
    else
        print_message "$RED" "❌ Failed to create application directory on server"
        print_message "$YELLOW" "Please check your SSH credentials"
        return 1
    fi
}

# Function to upload files to the server
upload_files() {
    print_message "$YELLOW" "Uploading application files to server..."
    
    # List of files to upload
    local main_files=("main.py" "requirements.txt" ".env" "Dockerfile")
    local success_count=0
    
    # Upload each file
    for file in "${main_files[@]}"; do
        if [ -f "$file" ]; then
            print_message "$YELLOW" "Uploading $file..."
            if scp -o StrictHostKeyChecking=no "$file" "$SERVER_USERNAME@$SERVER_IP:$APP_PATH/app/"; then
                print_message "$GREEN" "✅ $file uploaded successfully"
                ((success_count++))
            else
                print_message "$RED" "❌ Failed to upload $file"
            fi
        else
            print_message "$YELLOW" "⚠️ $file not found in current directory"
        fi
    done
    
    # Create systemd service file
    cat > esim-api.service << EOF
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
EOF
    
    # Upload service file
    if scp -o StrictHostKeyChecking=no esim-api.service "$SERVER_USERNAME@$SERVER_IP:$APP_PATH/"; then
        print_message "$GREEN" "✅ Service file uploaded successfully"
        ((success_count++))
    else
        print_message "$RED" "❌ Failed to upload service file"
    fi
    
    # Remove local service file
    rm esim-api.service
    
    # Return success if all files were uploaded
    if [ $success_count -eq $((${#main_files[@]} + 1)) ]; then
        return 0
    else
        return 1
    fi
}

# Function to set up the environment on the server
setup_environment() {
    print_message "$YELLOW" "Setting up environment on server..."
    
    # Create setup script
    cat > setup.sh << 'EOF'
#!/bin/bash
cd $APP_PATH

# Install Python and pip if needed
command -v python3 >/dev/null 2>&1 || { sudo apt-get update && sudo apt-get install -y python3 python3-pip; }

# Create virtual environment
python3 -m venv venv || python3 -m virtualenv venv

# Install dependencies
source venv/bin/activate && pip install -r app/requirements.txt

# Copy service file to systemd directory
sudo cp $APP_PATH/esim-api.service /etc/systemd/system/

# Reload systemd and enable/start service
sudo systemctl daemon-reload
sudo systemctl enable esim-api
sudo systemctl restart esim-api

# Set up health check script
echo '#!/bin/bash' > $APP_PATH/health_check.sh
echo 'curl -s http://localhost:8080/api/health || sudo systemctl restart esim-api' >> $APP_PATH/health_check.sh
chmod +x $APP_PATH/health_check.sh

# Add health check to crontab
(crontab -l 2>/dev/null; echo '*/5 * * * * $APP_PATH/health_check.sh') | crontab -
EOF
    
    # Replace variable in setup script
    sed -i "s|\$APP_PATH|$APP_PATH|g" setup.sh
    
    # Upload setup script
    if ! scp -o StrictHostKeyChecking=no setup.sh "$SERVER_USERNAME@$SERVER_IP:$APP_PATH/"; then
        print_message "$RED" "❌ Failed to upload setup script"
        rm setup.sh
        return 1
    fi
    
    # Execute setup script
    if ssh -o StrictHostKeyChecking=no "$SERVER_USERNAME@$SERVER_IP" "chmod +x $APP_PATH/setup.sh && $APP_PATH/setup.sh"; then
        print_message "$GREEN" "✅ Environment setup completed successfully"
        rm setup.sh
        return 0
    else
        print_message "$RED" "❌ Failed to set up environment on server"
        rm setup.sh
        return 1
    fi
}

# Function to verify deployment
verify_deployment() {
    print_message "$YELLOW" "Verifying deployment..."
    
    # Check if the service is running
    if ssh -o StrictHostKeyChecking=no "$SERVER_USERNAME@$SERVER_IP" "sudo systemctl status esim-api | grep 'Active: active'"; then
        print_message "$GREEN" "✅ Service is running"
        
        # Check if the API is responding
        if ssh -o StrictHostKeyChecking=no "$SERVER_USERNAME@$SERVER_IP" "curl -s http://localhost:8080/api/health | grep 'status.*ok'"; then
            print_message "$GREEN" "✅ API is responding correctly"
            print_message "$CYAN" "==============================================="
            print_message "$GREEN" "Deployment completed successfully!"
            print_message "$CYAN" "Your API is now accessible at:"
            echo "http://$SERVER_IP:8080"
            print_message "$CYAN" "API Documentation:"
            echo "http://$SERVER_IP:8080/docs"
            print_message "$CYAN" "==============================================="
            return 0
        else
            print_message "$RED" "❌ API is not responding correctly"
            print_message "$YELLOW" "Please check logs with: sudo journalctl -u esim-api"
            return 1
        fi
    else
        print_message "$RED" "❌ Service is not running"
        print_message "$YELLOW" "Please check logs with: sudo journalctl -u esim-api"
        return 1
    fi
}

# Main deployment workflow
if ! check_requirements; then
    exit 1
fi

print_message "$YELLOW" "Deploying to Cloudways server $SERVER_IP..."

if ! create_remote_directory; then
    print_message "$RED" "❌ Deployment failed: Could not create remote directory"
    exit 1
fi

if ! upload_files; then
    print_message "$RED" "❌ Deployment failed: Could not upload all required files"
    exit 1
fi

if ! setup_environment; then
    print_message "$RED" "❌ Deployment failed: Could not set up environment"
    exit 1
fi

if ! verify_deployment; then
    print_message "$RED" "❌ Deployment verification failed"
    exit 1
fi

print_message "$GREEN" "✅ Deployment completed successfully!" 
# eSIM Global - FastAPI Local Deployment Script
# This script sets up and runs the FastAPI application locally on Windows

# Colors for terminal output
function Write-Color {
    param (
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "===============================================" -Color Cyan
Write-Color "   eSIM Global FastAPI Local Deployment        " -Color Cyan
Write-Color "===============================================" -Color Cyan
Write-Color ""

Write-Color "This script will set up and run your FastAPI application locally." -Color Yellow
Write-Color ""

# Setup environment
Write-Color "Checking for Python..." -Color Yellow
$pythonVersion = python --version 2>&1
if (-not $?) {
    Write-Color "❌ Python not found! Please install Python 3.8 or higher." -Color Red
    Write-Color "Download from: https://www.python.org/downloads/" -Color Yellow
    exit 1
} else {
    Write-Color "✅ Found $pythonVersion" -Color Green
}

# Setup virtual environment if it doesn't exist
Write-Color "Setting up virtual environment..." -Color Yellow
if (-not (Test-Path -Path "venv")) {
    python -m venv venv
    if (-not $?) {
        Write-Color "❌ Failed to create virtual environment." -Color Red
        exit 1
    }
    Write-Color "✅ Virtual environment created" -Color Green
} else {
    Write-Color "✅ Virtual environment already exists" -Color Green
}

# Activate virtual environment
Write-Color "Activating virtual environment..." -Color Yellow
try {
    .\venv\Scripts\Activate
    if (-not $?) {
        throw "Failed to activate virtual environment"
    }
    Write-Color "✅ Virtual environment activated" -Color Green
} catch {
    Write-Color "❌ Failed to activate virtual environment: $_" -Color Red
    Write-Color "Try running this script as administrator or manually activate with: .\venv\Scripts\Activate" -Color Yellow
    exit 1
}

# Install dependencies
Write-Color "Installing dependencies..." -Color Yellow
pip install -r requirements.txt
if (-not $?) {
    Write-Color "❌ Failed to install dependencies." -Color Red
    exit 1
}
Write-Color "✅ Dependencies installed" -Color Green

# Check for .env file and create from example if it doesn't exist
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

# Make sure PORT is set properly in .env
Write-Color "Checking port configuration..." -Color Yellow
$envContent = Get-Content ".env" -Raw
if ($envContent -notmatch "LISTEN_PORT=") {
    Add-Content -Path ".env" -Value "`nLISTEN_PORT=8080"
    Write-Color "✅ Added LISTEN_PORT to .env file" -Color Green
}
if ($envContent -notmatch "LISTEN_HOST=") {
    Add-Content -Path ".env" -Value "LISTEN_HOST=0.0.0.0"
    Write-Color "✅ Added LISTEN_HOST to .env file" -Color Green
}

# Update main.py to respect environment variables for host and port
Write-Color "Checking if main.py needs updating..." -Color Yellow
$mainPyPath = "main.py"
$mainPyContent = Get-Content $mainPyPath -Raw

# If main.py doesn't contain LISTEN_PORT and LISTEN_HOST environment variables, add them
if ($mainPyContent -notmatch "LISTEN_PORT" -or $mainPyContent -notmatch "LISTEN_HOST") {
    Write-Color "Updating main.py to use environment variables for host and port..." -Color Yellow
    
    $updatedMain = $mainPyContent -replace "if __name__ == `"__main__`":([\s\S]*?)uvicorn\.run\(([^,]+),\s*host=[`"']([^`"']+)[`"'],\s*port=(\d+)", 'if __name__ == "__main__":{1}
    # Get port and host from environment variables
    port = int(os.getenv("LISTEN_PORT", 8080))
    host = os.getenv("LISTEN_HOST", "0.0.0.0")
    print(f"Starting server on {host}:{port}")
    uvicorn.run({2}, host=host, port=port'
    
    # If the regular expression didn't match, add a generic entry at the end
    if ($updatedMain -eq $mainPyContent) {
        $updatedMain = $mainPyContent + @"

# Added by deployment script
if __name__ == "__main__":
    # Get port and host from environment variables
    port = int(os.getenv("LISTEN_PORT", 8080))
    host = os.getenv("LISTEN_HOST", "0.0.0.0")
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
"@
    }
    
    Set-Content -Path $mainPyPath -Value $updatedMain
    Write-Color "✅ Updated main.py to use environment variables" -Color Green
} else {
    Write-Color "✅ main.py already configured to use environment variables" -Color Green
}

# Run the application
Write-Color "Starting FastAPI application..." -Color Yellow
Write-Color "Press Ctrl+C to stop the server" -Color Yellow
Write-Color ""
Write-Color "The application will be available at:" -Color Green
Write-Color "http://localhost:8080" -Color Cyan
Write-Color "API Documentation available at:" -Color Green
Write-Color "http://localhost:8080/docs" -Color Cyan
Write-Color ""

# Run the application
python main.py 
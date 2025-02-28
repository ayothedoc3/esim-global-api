# PowerShell script for deploying to Railway

# Function for colored output
function Write-Color {
    param (
        [Parameter(Position=0)]
        [string]$Message,
        [Parameter(Position=1)]
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Check if railway CLI is installed
$railwayInstalled = Get-Command railway -ErrorAction SilentlyContinue
if (-not $railwayInstalled) {
    Write-Color "Railway CLI not found!" "Red"
    Write-Color "Installing Railway CLI..." "Yellow"
    
    # For Windows, we need to use a different installation method
    Write-Color "Please install Railway CLI by following these steps:" "Yellow"
    Write-Color "1. Open PowerShell as Administrator" "Yellow"
    Write-Color "2. Run: npm install -g @railway/cli" "Yellow"
    Write-Color "3. After installation, restart this script" "Yellow"
    
    $installNow = Read-Host "Would you like to try installing Railway CLI now? (y/n)"
    if ($installNow -eq "y") {
        npm install -g @railway/cli
        Write-Color "Railway CLI installed. Please restart this script." "Green"
        exit
    } else {
        Write-Color "Please install Railway CLI manually before continuing." "Red"
        exit
    }
}

Write-Color "Logging in to Railway..." "Yellow"
railway login

Write-Color "Linking project..." "Yellow"
railway link

# Check if there are any uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Color "Uncommitted changes detected." "Yellow"
    $commit = Read-Host "Do you want to commit these changes before deploying? (y/n)"
    if ($commit -eq "y") {
        Write-Color "Committing changes..." "Yellow"
        git add .
        $commitMessage = Read-Host "Enter commit message"
        git commit -m "$commitMessage"
        Write-Color "Changes committed successfully!" "Green"
    }
}

Write-Color "Deploying to Railway..." "Yellow"
railway up

Write-Color "Deployment completed!" "Green"
railway status

Write-Color "Generating public URL..." "Yellow"
railway domain

Write-Color "Deployment URL:" "Green"
railway domain

git push 
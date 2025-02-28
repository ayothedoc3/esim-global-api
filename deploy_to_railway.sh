#!/bin/bash

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}Railway CLI not found!${NC}"
    echo -e "${YELLOW}Installing Railway CLI...${NC}"
    curl -fsSL https://railway.app/install.sh | sh
fi

echo -e "${YELLOW}Logging in to Railway...${NC}"
railway login

echo -e "${YELLOW}Linking project...${NC}"
railway link

# Check if there are any uncommitted changes
if [[ $(git status --porcelain) ]]; then
    echo -e "${YELLOW}Uncommitted changes detected.${NC}"
    read -p "Do you want to commit these changes before deploying? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Committing changes...${NC}"
        git add .
        read -p "Enter commit message: " commit_message
        git commit -m "$commit_message"
        echo -e "${GREEN}Changes committed successfully!${NC}"
    fi
fi

echo -e "${YELLOW}Deploying to Railway...${NC}"
railway up

echo -e "${GREEN}Deployment completed!${NC}"
railway status

echo -e "${YELLOW}Generating public URL...${NC}"
railway domain

echo -e "${GREEN}Deployment URL:${NC}"
railway domain 
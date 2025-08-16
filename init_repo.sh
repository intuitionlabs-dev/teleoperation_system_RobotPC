#!/bin/bash
# Initialize and prepare teleoperation-host repo

echo "Initializing teleoperation-host repository..."

# Initialize git
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Minimal teleoperation host for bimanual Piper robot"

echo ""
echo "Repository initialized! To push to GitHub:"
echo ""
echo "1. Create repo at: https://github.com/orgs/intuitionlabs-dev/repositories"
echo "   Name: teleoperation-host"
echo "   Description: Minimal ZMQ server for bimanual Piper robot control"
echo ""
echo "2. Then run:"
echo "   git remote add origin https://github.com/intuitionlabs-dev/teleoperation-host.git"
echo "   git branch -M main"
echo "   git push -u origin main"

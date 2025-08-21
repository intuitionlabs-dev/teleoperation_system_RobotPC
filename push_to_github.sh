#!/bin/bash
# Script to push the teleoperation system to GitHub

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Preparing to push to GitHub...${NC}"

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Initializing git repository...${NC}"
    git init
fi

# Add remote if it doesn't exist
if ! git remote | grep -q "origin"; then
    echo -e "${YELLOW}Adding remote origin...${NC}"
    git remote add origin https://github.com/intuitionlabs-dev/teleoperation_system_RobotPC_yam-piper.git
else
    echo -e "${GREEN}Remote origin already exists${NC}"
fi

# Stage all files
echo -e "${YELLOW}Staging files...${NC}"
git add -A

# Create commit
echo -e "${YELLOW}Creating commit...${NC}"
git commit -m "Complete teleoperation system for YAM and Piper robots

- Unified launch system for YAM with launch_yam_system.sh
- Fixed gravity compensation and initialization issues
- Integrated gello and i2rt libraries
- CAN cleanup scripts included
- Support for both Piper and YAM systems
- Clean, self-contained package with uv environment support"

# Force push to overwrite remote
echo -e "${YELLOW}Force pushing to GitHub (this will overwrite the remote)...${NC}"
git push -f origin main

echo -e "${GREEN}✓ Successfully pushed to GitHub!${NC}"
echo -e "${GREEN}Repository: https://github.com/intuitionlabs-dev/teleoperation_system_RobotPC_yam-piper${NC}"

# Clean up this script file
echo -e "${YELLOW}Cleaning up push script...${NC}"
rm -f "$0"
echo -e "${GREEN}✓ Push script removed${NC}"
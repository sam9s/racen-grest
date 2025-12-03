#!/bin/bash
# Simple backup script for pushing to GitHub

echo "Starting backup to GitHub..."

# Set the remote URL with token
git remote set-url github https://sam9s:$GITHUB_TOKEN@github.com/sam9s/racen-joveheal.git 2>/dev/null || \
git remote add github https://sam9s:$GITHUB_TOKEN@github.com/sam9s/racen-joveheal.git

# Get commit message (use default if not provided)
MESSAGE="${1:-Backup $(date '+%Y-%m-%d %H:%M')}"

# Stage all changes
git add -A

# Commit
git commit -m "$MESSAGE" || echo "Nothing new to commit"

# Push
git push github main

echo "Backup complete!"

#!/bin/bash
# Deploy Playwright optimizations to EC2

set -e

echo "========================================="
echo "Deploying Playwright Optimizations to EC2"
echo "========================================="
echo ""

# SSH connection details
SSH_KEY="C:/Users/mohit/key.pem"
SSH_HOST="ubuntu@13.60.63.52"
APP_DIR="~/app"

echo "Step 1: Pulling latest code from GitHub..."
ssh -i "$SSH_KEY" "$SSH_HOST" "cd $APP_DIR && git pull origin main"

echo ""
echo "Step 2: Rebuilding Docker containers..."
ssh -i "$SSH_KEY" "$SSH_HOST" "cd $APP_DIR && docker-compose -f docker-compose.prod.yml build api worker"

echo ""
echo "Step 3: Restarting services..."
ssh -i "$SSH_KEY" "$SSH_HOST" "cd $APP_DIR && docker-compose -f docker-compose.prod.yml up -d"

echo ""
echo "Step 4: Waiting for services to start..."
sleep 10

echo ""
echo "Step 5: Checking service health..."
ssh -i "$SSH_KEY" "$SSH_HOST" "cd $APP_DIR && docker-compose -f docker-compose.prod.yml ps"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test the API: curl https://api.darkproject.store/health"
echo "2. Monitor logs: ssh -i $SSH_KEY $SSH_HOST 'cd $APP_DIR && docker-compose -f docker-compose.prod.yml logs -f worker'"
echo "3. Test scraping: Should complete in 3-5 minutes (was 15+)"
echo ""

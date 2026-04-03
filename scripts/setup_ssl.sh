#!/bin/bash
set -e

DOMAIN="${1:-api.darkproject.store}"
EMAIL="${2:-your-email@example.com}"

echo "Setting up SSL for domain: $DOMAIN"

# Install certbot
sudo apt-get update
sudo apt-get install -y certbot

# Stop nginx temporarily to allow certbot to bind to port 80
cd ~/app
docker compose -f docker-compose.prod.yml stop nginx

# Get SSL certificate
sudo certbot certonly --standalone \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  -d "$DOMAIN"

# Create directory for SSL certs in project
mkdir -p ~/app/ssl

# Copy certificates (certbot renews them automatically)
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ~/app/ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ~/app/ssl/
sudo chown -R ubuntu:ubuntu ~/app/ssl

echo "✓ SSL certificates obtained and copied to ~/app/ssl/"
echo "✓ Certificates will auto-renew via certbot"
echo ""
echo "Next steps:"
echo "1. Update nginx.conf to use SSL"
echo "2. Update docker-compose.prod.yml to mount SSL certs"
echo "3. Restart containers"

#!/bin/bash
# Bootstrap Let's Encrypt certificate for mentoring.smallpeice.online
# Run once before `docker compose up`:  bash init-letsencrypt.sh

set -e

DOMAIN="mentoring.smallpeice.online"
EMAIL="admin@smallpeice.org"   # ← change to a real address for renewal alerts
CERT_PATH="./certbot/conf/live/$DOMAIN"

echo "==> Creating temporary self-signed cert so nginx can start..."
mkdir -p "$CERT_PATH"
openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "$CERT_PATH/privkey.pem" \
  -out    "$CERT_PATH/fullchain.pem" \
  -subj   "/CN=localhost" 2>/dev/null

echo "==> Starting nginx with temporary cert..."
docker compose up --force-recreate -d nginx
echo "    Waiting for nginx to be ready..."
sleep 5

echo "==> Removing temporary cert..."
rm -rf ./certbot/conf/live

echo "==> Requesting Let's Encrypt certificate..."
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

echo "==> Reloading nginx with real certificate..."
docker compose exec nginx nginx -s reload

echo ""
echo "Done! SSL certificate installed for $DOMAIN."
echo "Start the full stack with: docker compose up -d"

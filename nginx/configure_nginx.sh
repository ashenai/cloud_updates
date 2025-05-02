#!/bin/bash

# Configuration from environment variables
DOMAIN="${DOMAIN_NAME:-shen-ai.cloud}"
SSL_CERT_PATH="${SSL_CERT_PATH:-/etc/letsencrypt/live/${DOMAIN}/fullchain.pem}"
SSL_KEY_PATH="${SSL_KEY_PATH:-/etc/letsencrypt/live/${DOMAIN}/privkey.pem}"
APP_BASE_DIR="${APP_BASE_DIR:-/var/www/vhosts/shen-ai.cloud}"

# Create nginx config from template
sed "s|ssl_certificate .*|ssl_certificate ${SSL_CERT_PATH};|" ${APP_BASE_DIR}/cloud_updates/nginx/cloud_updates.conf > /tmp/cloud_updates.conf.tmp
sed -i "s|ssl_certificate_key .*|ssl_certificate_key ${SSL_KEY_PATH};|" /tmp/cloud_updates.conf.tmp
sed -i "s|server_name .*|server_name ${DOMAIN};|" /tmp/cloud_updates.conf.tmp

# Move the configured file to its final location
mv /tmp/cloud_updates.conf.tmp /etc/nginx/conf.d/cloud_updates.conf
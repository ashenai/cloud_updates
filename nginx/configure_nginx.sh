#!/bin/bash

# Default values if not provided through environment variables
SSL_CERT_PATH=${SSL_CERT_PATH:-"/etc/letsencrypt/live/shen-ai.cloud/fullchain.pem"}
SSL_KEY_PATH=${SSL_KEY_PATH:-"/etc/letsencrypt/live/shen-ai.cloud/privkey.pem"}

# Create nginx config from template
sed "s|ssl_certificate .*|ssl_certificate ${SSL_CERT_PATH};|" /var/www/vhosts/shen-ai.cloud/cloud_updates/nginx/cloud_updates.conf > /tmp/cloud_updates.conf.tmp
sed -i "s|ssl_certificate_key .*|ssl_certificate_key ${SSL_KEY_PATH};|" /tmp/cloud_updates.conf.tmp

# Move the configured file to its final location
mv /tmp/cloud_updates.conf.tmp /etc/nginx/conf.d/cloud_updates.conf
#!/bin/bash
set -e

# Configuration from environment variables
DOMAIN="${DOMAIN_NAME:-shen-ai.cloud}"
APP_BASE_DIR="${APP_BASE_DIR:-/var/www/vhosts/shen-ai.cloud}"
APP_USER="${APP_USER:-ashenai}"
APP_GROUP="${APP_GROUP:-psacln}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@shen-ai.cloud}"

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential libssl-dev libffi-dev \
    nginx uwsgi uwsgi-plugin-python3 supervisor git

# Install Certbot and its Nginx plugin
echo "Installing Certbot..."
sudo apt-get install -y snapd
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

echo "Creating application directories..."
sudo mkdir -p ${APP_BASE_DIR}/{cloud_updates,venv,logs,backups}

echo "Setting up uWSGI..."
sudo mkdir -p /etc/uwsgi/apps-available /etc/uwsgi/apps-enabled

echo "Setting up required permissions..."
sudo chown -R ${APP_USER}:${APP_GROUP} ${APP_BASE_DIR}
sudo chmod -R 750 ${APP_BASE_DIR}

echo "Creating temporary socket directory..."
sudo mkdir -p /tmp/cloud_updates
sudo chown ${APP_USER}:${APP_GROUP} /tmp/cloud_updates
sudo chmod 750 /tmp/cloud_updates

# Set up temporary Nginx configuration for SSL certificate generation
echo "Setting up temporary Nginx configuration..."
cat > /tmp/ssl_temp.conf << EOF
server {
    listen 80;
    server_name ${DOMAIN};
    root ${APP_BASE_DIR}/cloud_updates;
    location ~ /.well-known/acme-challenge {
        allow all;
    }
}
EOF

sudo mv /tmp/ssl_temp.conf /etc/nginx/conf.d/ssl_temp.conf
sudo nginx -t && sudo systemctl reload nginx

# Generate SSL certificate
echo "Generating SSL certificate..."
sudo certbot certonly --nginx --non-interactive --agree-tos --email ${ADMIN_EMAIL} -d ${DOMAIN}

# Remove temporary Nginx configuration
sudo rm /etc/nginx/conf.d/ssl_temp.conf
sudo nginx -t && sudo systemctl reload nginx

# Set up automatic certificate renewal
echo "Setting up automatic certificate renewal..."
sudo systemctl enable snapd.socket
sudo certbot renew --dry-run
(sudo crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | sudo crontab -

echo "Setup completed successfully!"
echo "SSL certificate has been generated and stored in /etc/letsencrypt/"
echo "Automatic certificate renewal has been configured to run daily at 3 AM"
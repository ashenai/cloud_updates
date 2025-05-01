#!/bin/bash
set -e

# Configuration
APP_DIR="/var/www/vhosts/shen-ai.cloud/cloud_updates"
VENV_DIR="/var/www/vhosts/shen-ai.cloud/venv"
BACKUP_DIR="/var/www/vhosts/shen-ai.cloud/backups"
LOG_DIR="/var/www/vhosts/shen-ai.cloud/logs"

# Create necessary directories
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

# Backup current version if exists
if [ -d "$APP_DIR" ]; then
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
    tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$(dirname $APP_DIR)" "$(basename $APP_DIR)"
fi

# Update or clone repository
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR"
    git fetch --all
    git reset --hard origin/main
else
    cd "$(dirname $APP_DIR)"
    git clone https://github.com/$GITHUB_REPOSITORY cloud_updates
fi

# Set up virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --no-cache-dir -r "$APP_DIR/requirements.txt"
pip install --no-cache-dir uwsgi

# Initialize database if needed
if [ ! -f "$APP_DIR/instance/cloud_updates.db" ]; then
    cd "$APP_DIR"
    flask db upgrade
fi

# Copy configurations
cp "$APP_DIR/config.py.example" "$APP_DIR/config.py"
sed -i "s/DEBUG = True/DEBUG = False/" "$APP_DIR/config.py"

# Copy uwsgi configuration
cp "$APP_DIR/uwsgi.ini" /etc/uwsgi/apps-available/cloud_updates.ini
ln -sf /etc/uwsgi/apps-available/cloud_updates.ini /etc/uwsgi/apps-enabled/

# Set permissions
chown -R ashenai:psacln "$APP_DIR" "$VENV_DIR" "$LOG_DIR"
chmod -R 750 "$APP_DIR" "$VENV_DIR"
chmod -R 770 "$LOG_DIR"

# Create and set permissions for uwsgi socket directory
mkdir -p /tmp/cloud_updates
chown ashenai:psacln /tmp/cloud_updates
chmod 750 /tmp/cloud_updates

# Restart services
systemctl restart uwsgi
plesk bin nginx --reconfigure-domain shen-ai.cloud
plesk bin nginx -r
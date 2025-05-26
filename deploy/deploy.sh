#!/bin/bash
set -e

# Configuration from GitHub environment variables
APP_DIR="${APP_BASE_DIR:-/var/www/vhosts/shen-ai.cloud}/cloud_updates"
VENV_DIR="${APP_BASE_DIR:-/var/www/vhosts/shen-ai.cloud}/venv"
BACKUP_DIR="${APP_BASE_DIR:-/var/www/vhosts/shen-ai.cloud}/backups"
LOG_DIR="${APP_BASE_DIR:-/var/www/vhosts/shen-ai.cloud}/logs"
APP_USER="${APP_USER:-ashenai}"
APP_GROUP="${APP_GROUP:-psacln}"

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
    git clone https://github.com/$REPO_FULL_NAME cloud_updates
fi

# Set up virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --no-cache-dir -r "$APP_DIR/requirements.txt"
pip install --no-cache-dir uwsgi

# Download spaCy language model
echo "Downloading spaCy language model..."
cd "$APP_DIR"
python -m app.utils.download_spacy_model

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
chown -R $APP_USER:$APP_GROUP "$APP_DIR" "$VENV_DIR" "$LOG_DIR"
chmod -R 750 "$APP_DIR" "$VENV_DIR"
chmod -R 770 "$LOG_DIR"

# Create and set permissions for uwsgi socket directory
mkdir -p /tmp/cloud_updates
chown $APP_USER:$APP_GROUP /tmp/cloud_updates
chmod 750 /tmp/cloud_updates

# Restart services
systemctl restart uwsgi
nginx -t && nginx -s reload
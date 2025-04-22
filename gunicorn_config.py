"""
Gunicorn configuration for the cloud_updates application.
"""
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = '/var/log/cloud_updates/access.log'
errorlog = '/var/log/cloud_updates/error.log'
loglevel = 'info'

# Process naming
proc_name = 'cloud_updates'

# Server mechanics
daemon = False
pidfile = '/var/run/cloud_updates/gunicorn.pid'
user = 'www-data'
group = 'www-data'

# SSL (uncomment if using HTTPS)
# keyfile = '/etc/ssl/private/cloud_updates.key'
# certfile = '/etc/ssl/certs/cloud_updates.crt'

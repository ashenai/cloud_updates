#!/bin/bash
source venv/bin/activate

nohup  venv/bin/uwsgi --stop /tmp/cloud_updates.pid; venv/bin/uwsgi --pidfile /tmp/cloud_updates.pid --ini cloud_updates/uwsgi.ini --socket /tmp/cloud_updates.sock
 --wsgi-file cloud_updates/wsgi.py --callable app --single-interpreter --chmod-socket=666 &
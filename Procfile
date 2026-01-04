web: cd web && gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class gevent --timeout 600 --graceful-timeout 600 app:app

#!/bin/sh
# entrypoint.sh

# Run migrations
poetry run python manage.py migrate

# Then run the main container command (passed to us as arguments)
exec "$@"
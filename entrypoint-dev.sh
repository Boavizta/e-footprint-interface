#!/bin/sh
# entrypoint.sh

# Run migrations
poetry run python manage.py migrate
poetry run python manage.py createcachetable

# Then run the main container command (passed to us as arguments)
exec "$@"

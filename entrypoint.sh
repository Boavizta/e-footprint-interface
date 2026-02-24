#!/bin/sh
# entrypoint.sh

# Run migrations
poetry run python manage.py migrate
poetry run python manage.py createcachetable

# Django Collect Static (assets)
poetry run python manage.py collectstatic --noinput --clear

# Then run the main container command (passed to us as arguments)
exec "$@"

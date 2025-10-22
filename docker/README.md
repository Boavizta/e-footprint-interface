# Setup your Docker environment

### Install Docker Desktop

Install Docker Desktop and choose the right architecture for you (e.g. arm64 for Mac Silicon) : [Link](https://www.docker.com/products/docker-desktop/)

### Install brew (for macOS)

On macOS, install [Homebrew](https://brew.sh/), so you can easily install some required stuff.

### Update your system /etc/hosts file

```console
# At the root directory of the repository
sudo sh -c 'cat docker/conf/host >> /etc/hosts'
```

### Setup HTTPs certificates for Localhost

```console
# Remember: need to install homebrew first
brew install nss mkcert
```

Or find another solution for your platform : Windows, Linux...

Source: [https://github.com/FiloSottile/mkcert](https://github.com/FiloSottile/mkcert)

### Install the CA Root for localhost

```console
mkcert -install
```

### Create self-signed certificates for boavizta.dev domain & sub-domains

```console
# At the root directory of the repository
mkcert -cert-file docker/conf/ssl/local-cert.pem -key-file docker/conf/ssl/local-key.pem "*.services.boavizta.dev" "*.boavizta.dev" "services.boavizta.dev" "boavizta.dev" "traefik"
```

Don't forget to restart your Chrome or Firefox.

### Run the stack

**The first step is to create your .env file. Simply copy the `.env.dist` and update the `EF_APP_PATH` to your project location.**

```console
cp .env.dist .env
# Edit .env and set EF_APP_PATH to your actual project path
```

**Note**: The `.env` file only needs `EF_APP_PATH` and `DATABASE_URL`. The `DJANGO_DOCKER` setting is automatically configured by `docker-compose.yml` and doesn't need to be in your `.env` file.

**Before the first launch, run this command to create the required network (one-time)**

```console
docker network create traefik
```

**First run the major dev services (traefik, django...)**

```console
docker compose --profile dev up -d
```

### Switching between development and production environments

When switching between different Docker environments (e.g., from `--profile dev` to `--profile prod` or vice versa), always stop and remove the current containers first to avoid port conflicts:

```console
# Stop all running containers for this project
docker compose --profile dev down

# Or stop all containers regardless of profile
docker compose down

# Then start the desired profile
docker compose --profile prod up -d
```

### Rebuilding Docker images

You need to rebuild your Docker images when:
- Poetry dependencies have changed (`pyproject.toml` or `poetry.lock` modified)
- Dockerfile has been updated
- System dependencies or base image need updating
- You encounter issues with stale cached layers

**Quick rebuild (with profile):**

```console
# Rebuild and restart with the dev profile
docker compose --profile dev up -d --build
```

**Manual rebuild steps:**

```console
# Stop running containers
docker compose --profile dev down

# Rebuild images
docker compose build

# Start containers with rebuilt images
docker compose --profile dev up -d
```

**Force complete rebuild (no cache):**

If you encounter caching issues or need a clean rebuild:

```console
docker compose build --no-cache
docker compose --profile dev up -d
```

**Rebuild specific service:**

```console
# Only rebuild the Django app service
docker compose build django
docker compose --profile dev up -d
```

**Note**: Always ensure your `poetry.lock` file is up to date before rebuilding. Run `poetry lock` locally if you've modified `pyproject.toml`.

**Useful commands for managing containers:**

```console
# View all running containers
docker compose ps

# View logs from all services
docker compose logs -f

# Stop containers without removing them
docker compose stop

# Stop and remove containers, networks, and volumes
docker compose down -v

# Clean up orphaned containers from old configurations
docker compose --profile dev up -d --remove-orphans
```

### List of local services

| Service Name | Service URL                               |
|--------------|-------------------------------------------|
| Web App      | https://efootprint.boavizta.dev/          |
| Traefik      | https://traefik.boavizta.dev/             |

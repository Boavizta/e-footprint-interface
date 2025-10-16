# Installation Guide

This guide covers two different setup approaches for running the e-footprint-interface application locally.

## Choose Your Setup

### Option 1: Docker Environment (Production-like)

For a production-like environment using Docker containers, see the **[Docker Setup Guide](docker/README.md)**.

This approach runs all services (Django, Postgres, Traefik) in Docker containers and is ideal for:
- Testing in a production-like environment
- Quick setup without local Python/Node dependencies
- Consistent environment across different machines

### Option 2: Local Development with IDE Debugging

For local development with full IDE debugging capabilities (recommended for active development).

---

## Local Development Setup (Option 2)

This setup runs Postgres in a Docker container while running Django locally in your IDE with full debugging support.

### Prerequisites

1. **Docker Desktop**: Install from [docker.com](https://www.docker.com/products/docker-desktop/)
2. **Poetry**: Follow instructions on [python-poetry.org](https://python-poetry.org/docs/#installation)
3. **Node.js**: Install via [nvm](https://github.com/nvm-sh/nvm)

### 1. Install Poetry

Follow the instructions on the [official poetry website](https://python-poetry.org/docs/#installation)

### 2. Install Dependencies

```bash
poetry install
```

### 3. Install Node.js and Dependencies

Download and install nvm (node version manager) from https://github.com/nvm-sh/nvm then install node:

```bash
nvm install node
```

Check installation:
```bash
node --version
npm --version
```

Install JavaScript dependencies:
```bash
npm install
```

### 4. Setup Docker Infrastructure

Start the Postgres database container:

```bash
docker compose -f docker-compose.infra.yml up -d
```

This will start only the Postgres database. Django will run locally on your machine.

**Note**: If you want to run the full production-like Docker environment (including Traefik reverse proxy), see the [Docker Setup Guide](docker/README.md) instead.

### 5. Configure Local Environment

Create a `.env.local` file in the root directory:

```bash
cat > .env.local << EOF
DJANGO_DOCKER=False
DATABASE_URL=postgresql://root:kakoukakou@localhost:5432/efootprint
EOF
```

### 6. Run Database Migrations

```bash
poetry run python manage.py migrate
poetry run python manage.py collectstatic
```

### 7. (Optional) Create Superuser

```bash
poetry run python manage.py createsuperuser
```

### 8. Run the Application

#### Terminal Method:

Start Bootstrap CSS compilation (in one terminal):
```bash
npm run watch
```

Run Django development server (in another terminal):
```bash
poetry run python manage.py runserver
```

#### IDE Method (PyCharm):

**Start Infrastructure:**
1. Open **Run → Edit Configurations...**
2. Add **Docker Compose** configuration:
   - **Name**: `Infrastructure (Postgres)`
   - **Compose file**: Select `docker-compose.infra.yml`
3. Run this configuration

**Start Django with Debugging:**
1. Open **Run → Edit Configurations...**
2. Add **Django Server** configuration:
   - **Name**: `Django Local (Debug)`
   - **Host**: `0.0.0.0`
   - **Port**: `8000`
   - **Environment variables**: Load from `.env.local`
3. Run or Debug this configuration
4. Set breakpoints in your code for interactive debugging!

### 9. Access the Application

- Local development: `http://localhost:8000`
- With Docker infrastructure: `https://efootprint.boavizta.dev` (requires hosts file setup)

# Run tests

## Python tests
```
poetry run python manage.py test
```

## E2E tests

To run all front end tests in console without opening the browser
```
npx cypress run --e2e
```

To check the tests in the browser, run this command
```
npx cypress open
```
Select E2E Testing in the Cypress window that opens and choose the browser you want to run the tests in.
Then click on the test file you want to run in the specs tabs

## js unit tests

```shell
npm install jest --global
jest
```

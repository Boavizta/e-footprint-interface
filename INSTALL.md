# Installation Guide

This guide covers three different setup approaches for running the e-footprint-interface application locally. Choose the one that best fits your development needs.

## Choose Your Setup

### Option 1: Full Local Development (Fastest - Recommended for Testing)

**Best for**: Running front-end tests quickly, rapid iteration, minimal setup

Runs everything locally (Django + SQLite) without Docker. This is the **fastest option** for E2E testing since there's no Docker overhead.

**Pros**:
- Fastest front-end test execution
- Minimal dependencies
- Quick startup/restart
- No Docker required

**Cons**:
- Uses SQLite instead of PostgreSQL (different from production)
- No debugging of PostgreSQL-specific issues

**Jump to**: [Full Local Setup](#full-local-development-option-1)

---

### Option 2: Hybrid Local Development (Best for Development)

**Best for**: Active development with IDE debugging and production-like database

Runs PostgreSQL in Docker while running Django locally. This gives you **IDE debugging capabilities** with a **production-like database**.

**Pros**:
- Full IDE debugging support
- Production-like PostgreSQL database
- Hot reload for code changes
- Fast iteration cycle

**Cons**:
- Slower front-end tests than full local (Docker overhead)
- Requires Docker for PostgreSQL

**Jump to**: [Hybrid Local Setup](#hybrid-local-development-option-2)

---

### Option 3: Full Docker Environment (Production-like)

**Best for**: Testing in production-like environment, sharing consistent setups

Runs all services (Django, PostgreSQL, Traefik) in Docker containers. See the **[Docker Setup Guide](docker/README.md)** for details.

**Pros**:
- Production-like environment
- Consistent across machines
- No local Python/Node setup needed

**Cons**:
- Slower iteration cycle
- Limited debugging capabilities
- Docker resource overhead

**Jump to**: [Full Docker Setup](#full-docker-environment-option-3)

---

## Full Local Development (Option 1)

This setup runs Django with SQLite locally - no Docker required. Perfect for fast front-end test execution.

### Prerequisites

1. **Poetry**: Follow instructions on [python-poetry.org](https://python-poetry.org/docs/#installation)
2. **Node.js**: Install via [nvm](https://github.com/nvm-sh/nvm)

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

Build the result charts bundle (required):
```bash
npm run build:result-charts:dev
```

If you edit files under `theme/static/scripts/result_charts/`, rebuild the bundle (or run a watcher):
```bash
npm run build:result-charts:dev -- --watch
```

### 4. Run Database Migrations

SQLite database will be created automatically:

```bash
poetry run python manage.py migrate
poetry run python manage.py createcachetable
poetry run python manage.py collectstatic
```

### 5. (Optional) Create Superuser

```bash
poetry run python manage.py createsuperuser
```

### 6. Run the Application

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

1. Open **Run → Edit Configurations...**
2. Add **Django Server** configuration:
   - **Name**: `Django Local (SQLite)`
   - **Host**: `0.0.0.0`
   - **Port**: `8000`
   - **Environment variables**: (leave empty - defaults to SQLite)
3. Run or Debug this configuration
4. Set breakpoints in your code for interactive debugging!

### 7. Access the Application

Open your browser to: `http://localhost:8000`

---

## Hybrid Local Development (Option 2)

This setup runs PostgreSQL in Docker while running Django locally in your IDE with full debugging support. This gives you a production-like database while maintaining fast development iteration.

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

Build the result charts bundle (required):
```bash
npm run build:result-charts:dev
```

If you edit files under `theme/static/scripts/result_charts/`, rebuild the bundle (or run a watcher):
```bash
npm run build:result-charts:dev -- --watch
```

### 4. Setup Docker Infrastructure

Start the PostgreSQL database container:

```bash
docker compose -f docker-compose.infra.yml up -d
```

This will start only the PostgreSQL database. Django will run locally on your machine.

**Note**: If you want to run the full production-like Docker environment (including Traefik reverse proxy), see [Option 3](#full-docker-environment-option-3) instead.

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
poetry run python manage.py createcachetable
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

Open your browser to: `http://localhost:8000`

### 10. Managing the PostgreSQL Container

Stop the database when not needed:
```bash
docker compose -f docker-compose.infra.yml down
```

View logs:
```bash
docker compose -f docker-compose.infra.yml logs -f
```

---

## Full Docker Environment (Option 3)

For a complete production-like environment with all services running in Docker (Django, PostgreSQL, Traefik), see the **[Docker Setup Guide](docker/README.md)**.

Note: the UI loads the result charts from a bundled file at `theme/static/bundles/result_charts.js`. When using the full Docker setup with the `/app` bind-mount, generate this bundle on your host before starting the stack:
```bash
npm install
npm run build:result-charts:dev
```

This approach is ideal for:
- Testing in a production-like environment with HTTPS
- Consistent environment across different machines
- Quick setup without local Python (Node is still needed to build the result charts bundle when using the bind-mount)
- Integration testing with reverse proxy (Traefik)

**Access after setup**: `https://efootprint.boavizta.dev`

---

# Run Tests

## Recommended Setup for Testing

**For fastest front-end test execution during development**, use **Option 1 (Full Local Development)** with SQLite. This eliminates Docker overhead and provides the quickest test runs. Then before deploying to prod, run tests in **Option 3 (Full Docker Environment)** to ensure compatibility with PostgreSQL.

To switch to full local mode for testing:
1. Stop any running Docker containers: `docker compose -f docker-compose.infra.yml down`
2. Remove or rename `.env.local` if it exists
3. Run migrations: `poetry run python manage.py migrate && poetry run python manage.py createcachetable`
4. Run tests as shown below

## Python Tests

```bash
poetry run python manage.py test
```

## E2E Tests (Playwright)

Playwright tests use Python and integrate with pytest. They can share fixtures with unit tests and create test models programmatically.

**First-time setup** (after `poetry install`):
```bash
# Install Playwright browsers
poetry run playwright install chromium
```

**Running E2E tests requires the Django server to be running:**

```bash
# Terminal 1: Start the Django server
poetry run python manage.py runserver

# Terminal 2: Run E2E tests
poetry run pytest tests/e2e/
```

**Run tests with visible browser (headed mode):**
```bash
poetry run pytest tests/e2e/ --headed
```

**Run a specific test with debugger:**
```bash
poetry run pytest tests/e2e/test_forms.py::test_unsaved_changes -s --pdb
```

**Run tests in parallel:**
```bash
# Run E2E tests in parallel (4 workers)
 poetry run pytest tests/e2e/ -n 4 --base-url http://localhost:8000
```

**Generate test code (record mode):**
```bash
poetry run playwright codegen http://localhost:8000/model_builder/
```

**Run with different browsers:**
```bash
poetry run pytest tests/e2e/ --browser firefox
poetry run pytest tests/e2e/ --browser webkit
```

**Override the server URL (e.g., for Docker):**
```bash
poetry run pytest tests/e2e/ --headed --base-url https://efootprint.boavizta.dev
```

## JavaScript Unit Tests

```bash
npm install jest --global
jest
```

---

# Switching Between Setups

You can easily switch between the three setup options:

## From Full Local (Option 1) to Hybrid (Option 2)

1. Start PostgreSQL container:
   ```bash
   docker compose -f docker-compose.infra.yml up -d
   ```

2. Create `.env.local`:
   ```bash
   cat > .env.local << EOF
   DJANGO_DOCKER=False
   DATABASE_URL=postgresql://root:kakoukakou@localhost:5432/efootprint
   EOF
   ```

3. Run migrations:
   ```bash
   poetry run python manage.py migrate
   poetry run python manage.py createcachetable
   ```

## From Hybrid (Option 2) to Full Local (Option 1)

1. Stop PostgreSQL container:
   ```bash
   docker compose -f docker-compose.infra.yml down
   ```

2. Remove `.env.local`:
   ```bash
   rm .env.local
   ```

3. SQLite will be used automatically (no additional configuration needed)

## From Any Option to Full Docker (Option 3)

See the [Docker Setup Guide](docker/README.md) for complete instructions.

# Release Process

This document describes the steps to create and deploy a new release.

## 1. Pre-release: Update Version and Dependencies

### Update interface version
Edit version in [pyproject.toml](pyproject.toml):
```toml
[tool.poetry]
version = "x.y.z"
```

### Update documentation
- Update [CHANGELOG.md](CHANGELOG.md) with all changes since last release
- Update [README.md](README.md) if needed

### Update dependencies
```shell
# Update Python dependencies
poetry update

# Update Node.js if necessary
nvm install node

# Update npm dependencies
npm install
```

**Note**: Clever Cloud deploys using Docker, which installs dependencies via `poetry install` in the Dockerfile. No need to generate `requirements.txt`.

## 2. Testing

### Ensure CSS is up to date
```shell
npm run watch
```

### Run all tests
Install Jest globally if not already done:
```shell
npm install jest --global
```

Run test suites:
```shell
# Python tests__old (soon to be deprecated)
poetry run python manage.py test tests__old

poetry run pytest tests -n 4 --base-url http://localhost:8000

# JavaScript unit tests
jest
```

All tests must pass before proceeding.

## 3. Create Release Commit and PR

### Create version commit
Create a commit with message starting with `[Vx.y.z]`:
```shell
git add .
git commit -m "[Vx.y.z] Release description"
```

### Create Pull Request
1. Push your branch to GitHub
2. Create a PR to `main` branch
3. Wait for CI to pass
4. Request review from team members

### Deploy to PreProd (staging)
```shell
git push clever <feature-branch-name>:master
```

Test the PreProd deployment at: https://dev.e-footprint.boavizta.org

## 4. Deploy to Clever Cloud

Once the PR is approved and merged to `main`:

### Deploy to Production
```shell
git push clever-prod main:master
```

The production site will be available at: https://e-footprint.boavizta.org

**Note**: Both PreProd and Production Clever Cloud environments expect code pushed to their `master` branch.

See [DEPLOY_TO_PROD.md](DEPLOY_TO_PROD.md) for detailed deployment instructions and troubleshooting.

## 5. Post-deployment

- Verify the application works on both PreProd and Production
- Monitor Clever Cloud logs for any errors
- Create a GitHub release with the version tag and changelog

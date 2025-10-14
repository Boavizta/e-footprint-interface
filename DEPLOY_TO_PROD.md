# Deployment to Production

This project is deployed to **Clever Cloud** for both PreProd (staging) and Production environments.

## Prerequisites

### 1. SSH Key Registration
Register your SSH public key in Clever Cloud:
1. Go to https://console.clever-cloud.com/
2. Navigate to your profile → SSH Keys
3. Add your public key from `~/.ssh/id_rsa.pub`

### 2. Git Remotes Setup
Add Clever Cloud git remotes to your repository (only needed once):

```shell
# PreProd (staging)
git remote add clever git+ssh://git@push-n3-par-clevercloud-customers.services.clever-cloud.com/app_60266226-9ce3-4b53-9b14-57e1628d0ac5.git

# Production
git remote add clever-prod git+ssh://git@push-n3-par-clevercloud-customers.services.clever-cloud.com/app_d801760c-ba09-49e8-8c87-7ca6b2afa377.git
```

Verify remotes are configured:
```shell
git remote -v
```

## Pre-deployment Checklist

### 1. Ensure dependencies are up to date
Clever Cloud uses Docker deployment, which runs `poetry install` from your `Dockerfile`. Ensure `poetry.lock` is up to date:

```shell
poetry update
```

**Note**: Docker deployment installs dependencies from `poetry.lock` and `pyproject.toml`, not from `requirements.txt`.

### 2. Run deployment checks
```shell
poetry run python manage.py check --deploy
```

## Deployment Commands

### Deploy to PreProd (Staging)
```shell
# Push your local branch to Clever Cloud's master branch
git push clever <local-branch>:master

# Example: deploy from main branch
git push clever main:master
```

PreProd URL: https://dev.e-footprint.boavizta.org

### Deploy to Production
```shell
# Push your local branch to Production's master branch
git push clever-prod <local-branch>:master

# Example: deploy from main branch
git push clever-prod main:master
```

Production URL: https://e-footprint.boavizta.org

**Important Notes**:
- Always push to `master` as the remote branch name: `git push clever <local-branch>:master`
- The deployment is automatic after the push
- Clever Cloud builds the Docker image using your `Dockerfile`, which runs `poetry install` to install dependencies

## Post-deployment Verification

1. **Check deployment logs** in Clever Cloud console:
   - Go to your application → Logs
   - Verify there are no errors during build and deployment

2. **Test the deployed application**:
   - Visit the deployed URL
   - Test critical functionality
   - Check for any errors in browser console

3. **Monitor application logs**:
   - Watch for any runtime errors
   - Verify database connections are working

## Environment Configuration

### Clever Cloud Environment Variables
The following environment variables should be configured in Clever Cloud console:

**Required**:
- `DJANGO_CLEVER_CLOUD=True` - Activates production settings
- `DATABASE_URL` - PostgreSQL connection string (auto-configured by Clever Cloud)
- `SECRET_KEY` - Django secret key (generate a secure random string)

**Optional**:
- `DEBUG=False` - Should always be False in production
- Custom settings as needed

### Settings Configuration
The application automatically detects Clever Cloud environment and applies production settings (see `e_footprint_interface/settings.py:163-184`):
- HTTPS enforcement (HSTS)
- Secure cookies
- Allowed hosts configuration
- CSRF trusted origins

## Database Management

### Run migrations on Clever Cloud
Migrations run automatically during deployment. If you need to run them manually:

```shell
# Via Clever Cloud console terminal or CLI
clever ssh
python manage.py migrate
```

### Access database directly
Install Clever Cloud CLI and connect:
```shell
# Install Clever Cloud CLI
npm install -g clever-cloud

# Login
clever login

# Link to your application
clever link <app-id>

# Connect to PostgreSQL
clever psql
```

Or use a PostgreSQL client with the `DATABASE_URL` from Clever Cloud environment variables.

## Troubleshooting

### Deployment fails
1. Check Clever Cloud logs for build errors
2. Verify `poetry.lock` and `pyproject.toml` are committed
3. Ensure all environment variables are set correctly in Clever Cloud console

### Application doesn't start
1. Check application logs in Clever Cloud console
2. Verify database connection string is correct
3. Run `python manage.py check --deploy` locally to catch configuration issues

### Database migration issues
1. Check migration files are committed to git
2. Manually run migrations via Clever Cloud SSH
3. Check database connectivity

## Rolling Back

If a deployment introduces issues:

1. **Revert to previous version**:
```shell
# Get the commit hash of the last working version
git log

# Force push the old version
git push clever <commit-hash>:master --force
```

2. **Monitor the rollback**:
- Check Clever Cloud logs
- Verify the application is working

3. **Fix the issue** in a new branch before redeploying

## Additional Resources

- [Clever Cloud Documentation](https://www.clever-cloud.com/doc/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)

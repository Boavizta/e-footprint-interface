"""
Django settings for e_footprint_interface project.
"""
import os
from pathlib import Path
import environ

# ============================================================================
# BASE CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variables
env = environ.Env(DEBUG=(bool, False))

# Load environment file (.env.local takes precedence for local development)
env_file_local = os.path.join(BASE_DIR, ".env.local")
env_file = os.path.join(BASE_DIR, ".env")

if os.path.isfile(env_file_local):
    env.read_env(env_file_local)
elif os.path.isfile(env_file):
    env.read_env(env_file)
elif os.getenv('DJANGO_CLEVER_CLOUD') != 'True':
    raise Exception("No local .env or .env.local file found. Please create one.")

# ============================================================================
# SECURITY SETTINGS
# ============================================================================

# Default insecure key for development (override in production via env var)
SECRET_KEY = "django-insecure--3#!ddceds#0n$a6(r$8=j*%-r05rm5x!en1wqhg@^2cjnvg4r"
DEBUG = True
ALLOWED_HOSTS = []

# Security headers
X_FRAME_OPTIONS = "SAMEORIGIN"
CSP_FRAME_ANCESTORS = ["'self'"]

# ============================================================================
# APPLICATION DEFINITION
# ============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "model_builder",
    "theme",
    "django_browser_reload",
    "django_bootstrap5",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

# Add latency middleware for non-production environments
if os.getenv('DJANGO_PROD') != 'True':
    MIDDLEWARE.append('e_footprint_interface.latency_middleware.NetworkLatencyMiddleware')

ROOT_URLCONF = "e_footprint_interface.urls"
WSGI_APPLICATION = "e_footprint_interface.wsgi.application"

# ============================================================================
# TEMPLATES
# ============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ============================================================================
# DATABASE
# ============================================================================

# Default to SQLite (will be overridden by environment-specific config below)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ============================================================================
# AUTHENTICATION & PASSWORD VALIDATION
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC FILES
# ============================================================================

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# ============================================================================
# DJANGO BROWSER RELOAD
# ============================================================================

INTERNAL_IPS = ["127.0.0.1"]

# ============================================================================
# DEFAULT SETTINGS
# ============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# ENVIRONMENT-SPECIFIC CONFIGURATION
# ============================================================================

# Local development with PyCharm (using .env.local)
if os.getenv('DJANGO_DOCKER') == 'False' and os.path.isfile(env_file_local):
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
    DATABASES = {"default": env.db()}

# Local Docker environment
elif os.getenv('DJANGO_DOCKER') == 'True':
    ALLOWED_HOSTS = ["efootprint.boavizta.dev", "*.boavizta.dev"]
    DATABASES = {"default": env.db()}
    CSRF_TRUSTED_ORIGINS = ["https://*.boavizta.dev"]

# Clever Cloud production/staging
elif os.getenv('DJANGO_CLEVER_CLOUD') == 'True':
    # Security settings
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECRET_KEY = os.getenv("SECRET_KEY")
    DEBUG = False

    # Hosts configuration
    ALLOWED_HOSTS = [
        "dev.e-footprint.boavizta.org",
        "e-footprint.boavizta.org",
        "*.boavizta.org",
        "*.*.boavizta.org",
        "*.cleverapps.io"
    ]
    CSRF_TRUSTED_ORIGINS = ["https://*.boavizta.org", "https://*.cleverapps.io"]

    # Database configuration
    DATABASES = {"default": env.db()}
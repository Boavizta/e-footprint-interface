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
    "e_footprint_interface.computation_memory_middleware.ComputationMemoryMiddleware",
    "e_footprint_interface.session_performance_middleware.SessionPerformanceMiddleware",
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
                "model_builder.adapters.context_processors.edge_modeling_doc_url",
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

# Cache busting: appends content hash to filenames (e.g., app.js -> app.a1b2c3d4.js)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}

# ============================================================================
# CACHES
# ============================================================================

REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    redis_backend = "django.core.cache.backends.redis.RedisCache"
    redis_location = REDIS_URL
else:
    redis_backend = "django.core.cache.backends.locmem.LocMemCache"
    redis_location = "redis-cache"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default-cache",
    },
    "redis": {
        "BACKEND": redis_backend,
        "LOCATION": redis_location,
    },
    "postgres": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    },
}

# ============================================================================
# DJANGO BROWSER RELOAD
# ============================================================================

INTERNAL_IPS = ["127.0.0.1"]

# ============================================================================
# DEFAULT SETTINGS
# ============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Browser sessions and their small server-side indexes/preferences share this lifetime.
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60


def optional_env_bool(name: str, default: bool | None = None) -> bool | None:
    """Read an optional deployment fact without turning an absent value into an assurance."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


IS_CLEVER_CLOUD_DEPLOYMENT = os.getenv("DJANGO_CLEVER_CLOUD") == "True"
DATA_PRIVACY_OPERATOR_NAME = os.getenv(
    "DATA_PRIVACY_OPERATOR_NAME", "Boavizta" if IS_CLEVER_CLOUD_DEPLOYMENT else ""
)
DATA_PRIVACY_HOSTING_PROVIDER_NAME = os.getenv(
    "DATA_PRIVACY_HOSTING_PROVIDER_NAME", "Clever Cloud" if IS_CLEVER_CLOUD_DEPLOYMENT else ""
)
DATA_PRIVACY_HOSTING_REGION = os.getenv(
    "DATA_PRIVACY_HOSTING_REGION", "Paris" if IS_CLEVER_CLOUD_DEPLOYMENT else ""
)
DATA_PRIVACY_SECURITY_CONTACT = os.getenv(
    "DATA_PRIVACY_SECURITY_CONTACT",
    "vincent.villet@publicissapient.com" if IS_CLEVER_CLOUD_DEPLOYMENT else "",
)
DATA_PRIVACY_HTTPS_ENABLED = optional_env_bool(
    "DATA_PRIVACY_HTTPS_ENABLED", True if IS_CLEVER_CLOUD_DEPLOYMENT else None
)
DATA_PRIVACY_POSTGRES_ENCRYPTED_AT_REST = optional_env_bool(
    "DATA_PRIVACY_POSTGRES_ENCRYPTED_AT_REST", True if IS_CLEVER_CLOUD_DEPLOYMENT else None
)
DATA_PRIVACY_POSTGRES_BACKUPS_ENABLED = optional_env_bool(
    "DATA_PRIVACY_POSTGRES_BACKUPS_ENABLED", True if IS_CLEVER_CLOUD_DEPLOYMENT else None
)
DATA_PRIVACY_POSTGRES_BACKUP_FREQUENCY = os.getenv(
    "DATA_PRIVACY_POSTGRES_BACKUP_FREQUENCY", "daily" if IS_CLEVER_CLOUD_DEPLOYMENT else ""
)
DATA_PRIVACY_POSTGRES_BACKUP_RETENTION_DAYS = int(
    os.getenv("DATA_PRIVACY_POSTGRES_BACKUP_RETENTION_DAYS", "7" if IS_CLEVER_CLOUD_DEPLOYMENT else "0")
)
DATA_PRIVACY_POSTGRES_BACKUPS_ENCRYPTED_AT_REST = optional_env_bool(
    "DATA_PRIVACY_POSTGRES_BACKUPS_ENCRYPTED_AT_REST", False if IS_CLEVER_CLOUD_DEPLOYMENT else None
)
DATA_PRIVACY_PUBLIC_SHARED_INSTANCE = optional_env_bool(
    "DATA_PRIVACY_PUBLIC_SHARED_INSTANCE", IS_CLEVER_CLOUD_DEPLOYMENT
)

# Base URL of the published e-footprint mkdocs site. Used to render `{doc:slug}`
# placeholders as outbound links from interface help content.
MKDOCS_BASE_URL = os.getenv("MKDOCS_BASE_URL", "https://boavizta.github.io/e-footprint")

# URL of the canonical "web vs edge modeling" explanation page on mkdocs.
# Surfaced in the edge-modeling toggle popover.
EDGE_MODELING_DOC_URL = os.getenv(
    "EDGE_MODELING_DOC_URL", f"{MKDOCS_BASE_URL}/web_vs_edge/")

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

import io
import os
from pathlib import Path
from urllib.parse import urlparse

from django.contrib import staticfiles
from efootprint.core.all_classes_in_order import ALL_EFOOTPRINT_CLASSES
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

import environ
from google.cloud import secretmanager

from model_builder.efootprint_extensions.usage_pattern_from_form import UsagePatternFromForm

_extension_classes = [UsagePatternFromForm]
MODELING_OBJECT_CLASSES_DICT = {modeling_object_class.__name__: modeling_object_class
                                for modeling_object_class in ALL_EFOOTPRINT_CLASSES + _extension_classes}

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure--3#!ddceds#0n$a6(r$8=j*%-r05rm5x!en1wqhg@^2cjnvg4r"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = '/static/'

env = environ.Env(DEBUG=(bool, False))
env_file = os.path.join(BASE_DIR, ".env")
if os.path.isfile(env_file):
    env.read_env(env_file)
elif os.environ.get("GOOGLE_CLOUD_PROJECT", None):
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = secretmanager.SecretManagerServiceClient()
    settings_name = os.environ.get("SETTINGS_NAME", "django_settings")
    name = f"projects/{project_id}/secrets/{settings_name}/versions/latest"
    payload = client.access_secret_version(name=name).payload.data.decode("UTF-8")
    env.read_env(io.StringIO(payload))
else:
    raise Exception("No local .env or GOOGLE_CLOUD_PROJECT detected. No secrets found.")

ALLOWED_HOSTS = []

# Application definition

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
    'django_bootstrap5',
]

INTERNAL_IPS = [
    "127.0.0.1",
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

if os.getenv('DJANGO_PROD') != 'True':
    MIDDLEWARE.append('e_footprint_interface.latency_middleware.NetworkLatencyMiddleware')

ROOT_URLCONF = "e_footprint_interface.urls"

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

WSGI_APPLICATION = "e_footprint_interface.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if os.getenv('DJANGO_PROD') == 'True':
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_PRELOAD = True
    SECRET_KEY = env("SECRET_KEY")

    # SECURITY WARNING: don't run with debug turned on in production!
    # Change this to "False" when you are ready for production
    DEBUG = False

    APPENGINE_URL = env("APPENGINE_URL", default=None)
    if APPENGINE_URL:
        # Ensure a scheme is present in the URL before it's processed.
        if not urlparse(APPENGINE_URL).scheme:
            APPENGINE_URL = f"https://{APPENGINE_URL}"

        main_url_netloc = urlparse(APPENGINE_URL).netloc
        ALLOWED_HOSTS = [main_url_netloc]

        # Get app engine versions to allow their URLs
        credentials = GoogleCredentials.get_application_default()
        service = discovery.build('appengine', 'v1', credentials=credentials)
        versions = service.apps().services().versions().list(
            appsId='e-footprint-interface', servicesId="default").execute()['versions']
        for version in versions:
            ALLOWED_HOSTS.append(f"{version['id']}-dot-{main_url_netloc}")

        CSRF_TRUSTED_ORIGINS = [APPENGINE_URL]
        SECURE_SSL_REDIRECT = True
    else:
        ALLOWED_HOSTS = ["*"]
    # [END gaestd_py_django_csrf]

    DATABASES = {"default": env.db()}

    # If the flag as been set, configure to use proxy
    if os.getenv("USE_CLOUD_SQL_AUTH_PROXY", None):
        DATABASES["default"]["HOST"] = "127.0.0.1"
        DATABASES["default"]["PORT"] = 5432

    # [END gaestd_py_django_database_config]
    # [END db_setup]

X_FRAME_OPTIONS = "SAMEORIGIN"
CSP_FRAME_ANCESTORS = ["'self'"]

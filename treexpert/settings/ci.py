from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ci",
        "USER": "postgres",
        "PASSWORD": "Password",
        "HOST": "localhost",
        "PORT": "5432",
    },
}

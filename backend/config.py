import os
import tempfile
from pathlib import Path


class DevConfig:
    DEBUG = True
    APP_ROOT = Path("./outputs").resolve()
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{APP_ROOT}/meta.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestingConfig:
    TESTING = True
    DEBUG = True
    APP_ROOT = Path(tempfile.mkdtemp())
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{APP_ROOT}/meta.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductConfig:
    USER_HOME = os.getenv("HOME")
    APP_ROOT = Path(f"{USER_HOME}/.smart_remocon/").resolve()
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{APP_ROOT}/meta.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


config = {
    "development": "backend.config.DevConfig",
    "testing": "backend.config.TestingConfig",
    "product": "backend.config.ProductConfig",
    "default": "backend.config.DevConfig",
}


def cofigure_app(app):
    config_name = os.getenv("FLASK_CONFIGURATION", "default")
    config_obj = config.get(config_name)
    if config_obj is None:
        config_obj = config["default"]
    app.config.from_object(config_obj)

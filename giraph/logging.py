"""Logging"""

# stdlib
from logging import getLogger, StreamHandler
from os import environ

logger = getLogger("giraph")
logger.addHandler(StreamHandler())
logger.setLevel(environ.get("LOG_LEVEL", "INFO"))

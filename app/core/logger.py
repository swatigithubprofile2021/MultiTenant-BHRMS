import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings


def setup_logging(level=logging.INFO):
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file = RotatingFileHandler(
        f"{settings.LOG_PATH}/app.log", maxBytes=10_000_000, backupCount=5
    )
    file.setFormatter(formatter)

    logging.root.setLevel(level)
    logging.root.handlers = [console, file]


setup_logging()
logger = logging.getLogger(__name__)

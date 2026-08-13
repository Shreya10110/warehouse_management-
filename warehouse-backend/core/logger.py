import logging


def configure_logging() -> logging.Logger:
    """Configure process-wide structured console logging and return the app logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger("warehouse")

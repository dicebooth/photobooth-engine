import logging


def setup_logging(log_file: str) -> None:
    """
    Method which configures the application logger on the given log file.
    The log file path is injected by the composition root.

    :param log_file: path of the log file
    """
    from photobooth.consts import LOGGER_NAME

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return  # avoid duplicates

    handler = logging.FileHandler(
        log_file,  # single log file
        mode="a",                # append
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

# tail -f photobooth-upload.log
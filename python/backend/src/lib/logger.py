import logging

LOGGER_NAME = "experiment_tracker.backend"


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    return logging.getLogger(name)


logger = logging.getLogger(LOGGER_NAME)

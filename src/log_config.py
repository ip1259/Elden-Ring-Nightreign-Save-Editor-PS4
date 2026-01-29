import logging
import logging.config
import os


def setup_logging(default_path='logs', default_level=logging.DEBUG):
    """
    Setup logging configuration
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(default_path):
        os.makedirs(default_path)

    log_file_path = os.path.join(default_path, "app.log")

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                # Detailed format: Time - Level - [Logger Name] [File:Line] - Message
                "format": "%(asctime)s - %(levelname)s - [%(name)s] [%(filename)s:%(lineno)d] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",  # Only show INFO and above in console
                "formatter": "detailed",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "WARNING",  # Keep detailed logs in file
                "formatter": "detailed",
                "filename": log_file_path,
                "maxBytes": 5 * 1024 * 1024,  # 5MB per file
                "backupCount": 5,             # Keep 5 backup files
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {  # Root logger configuration
                "handlers": ["console", "file"],
                "level": default_level,
            },
        },
    }

    # Apply the configuration dictionary
    logging.config.dictConfig(logging_config)

    # Return a logger instance for the caller
    return logging.getLogger("AppRoot")

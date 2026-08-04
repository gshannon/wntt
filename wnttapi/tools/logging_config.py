import logging


# Force all logging to console, for use by standalone utilities.
# Note this is already the case for the dev configuration, but doesn't hurt to be explicit here.
def force_console_logging(level=logging.INFO):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            "{asctime} {levelname} {module} {funcName} {message}",
            style="{",
        )
    )

    root = logging.getLogger()
    root.handlers = [console_handler]
    root.setLevel(level)

    for name in logging.root.manager.loggerDict:
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        # Optional:
        # lg.setLevel(logging.NOTSET)  # defer to root's level

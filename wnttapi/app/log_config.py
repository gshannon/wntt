import json
import logging
import os
import pathlib

logger = logging.getLogger(__name__)

_default_file_path = "/data/log_levels.json"
_valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_last_mtime: float | None = None


def refresh_log_levels(filepath: str = _default_file_path) -> None:
    """Re-apply logger levels from filepath if it changed since the last call. Cheap no-op
    in the common case. Never raises; any failure is logged and skipped, leaving levels as-is."""
    global _last_mtime
    try:
        mtime = os.stat(filepath).st_mtime
    except FileNotFoundError:
        return
    except OSError as e:
        logger.error("Could not stat log level config %s: %s", filepath, e)
        return

    if mtime == _last_mtime:
        return
    _apply_log_levels(filepath)
    _last_mtime = mtime


def _apply_log_levels(filepath: str) -> None:
    try:
        levels = json.loads(pathlib.Path(filepath).read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Could not read/parse log level config %s: %s", filepath, e)
        return

    if not isinstance(levels, dict):
        logger.error("Log level config %s must be a JSON object", filepath)
        return

    for name, level in levels.items():
        level_upper = str(level).upper()
        if level_upper not in _valid_levels:
            logger.error(
                "Ignoring invalid log level %r for logger %r in %s", level, name, filepath
            )
            continue
        logging.getLogger(name).setLevel(level_upper)
        logger.info("Set logger %r to level %s (from %s)", name, level_upper, filepath)

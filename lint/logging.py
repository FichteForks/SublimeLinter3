from contextlib import contextmanager
from functools import partial
import logging
import os
import threading


BASE_PREFIX = "[SublimeLinter] "
BASE_FORMAT = "%(message)s"
NAMESPACE = __name__

# Our created loggers.
# Needed to set the level for each individually.
_loggers = set()
# The associated handlers.
# Needed to remove the previous one in case a logger is "re-created".
_handlers = {}


def _build_logger(name, fmt, propagate=True):
    logger = logging.getLogger(name)
    logger.propagate = propagate
    _loggers.add(logger)
    if logger in _handlers:
        logger.removeHandler(_handlers[logger])

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    _handlers[logger] = handler

    return logger


def setLevel(level):
    """Set the logging level for all created loggers."""
    for logger in _loggers:
        logger.setLevel(level)


def set_debug_level(is_debug):
    """Set the logging level based on a boolean."""
    level = logging.DEBUG if is_debug else logging.INFO
    setLevel(level)


def getLinterClsLogger(linter_cls):
    linter_name = linter_cls.name

    name = "{}.{}".format(NAMESPACE, linter_name)
    fmt = "{}[{}] {}".format(BASE_PREFIX, linter_name, BASE_FORMAT)
    return _build_logger(name, fmt, propagate=False)


def getLinterLogger(linter, task_id=None):
    linter_name = linter.name
    file_path = linter.view.file_name() or "<untitled {}>".format(linter.view.buffer_id())
    file_name = os.path.basename(file_path)

    name = "{}.{}.{}".format(NAMESPACE, linter_name, linter.view.id())
    fmt = "{}#{} [{}] ({}) {}".format(BASE_PREFIX, task_id, linter_name, file_name, BASE_FORMAT)
    return _build_logger(name, fmt, propagate=False)


# Configure base logger for the entire package
package_name = __package__.split('.')[0]
base_logger = _build_logger(package_name, BASE_PREFIX + BASE_FORMAT)
setLevel(logging.INFO)


# Map thread idents to an active logger
_thread_logger_map = {}
# Used when no linter-specific logger is active
default_logger = logging.getLogger(__name__)


@contextmanager
def logger_context(logger):
    key = threading.get_ident()
    _thread_logger_map[key] = logger
    yield
    del _thread_logger_map[key]


def get_current_logger():
    """Find the active logger for the current thread."""
    logger = _thread_logger_map.get(threading.get_ident())
    if not logger:
        logger = base_logger
    return logger


def _wrapper(func_name, *args, **kwargs):
    return getattr(get_current_logger(), func_name)(*args, **kwargs)


# Create thread-aware logging functions
func_names = ('critical', 'exception', 'error', 'warning', 'info', 'debug', 'isEnabledFor')
for func_name in func_names:
    globals()[func_name] = partial(_wrapper, func_name)

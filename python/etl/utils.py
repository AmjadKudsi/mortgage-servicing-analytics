"""
utils.py — Logging setup and shared helpers.
"""

import os
import sys
import time
import logging
import functools
import yaml


def setup_logging(log_file="reports/etl_log.txt"):
    """Configure logging to both console and file."""
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode="w"),
        ],
    )
    return logging.getLogger("etl")


def load_config(config_path):
    """Load and return the YAML config file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def timed(func):
    """Decorator that logs execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        log = logging.getLogger("etl")
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        log.info(f"  [{func.__name__}] completed in {elapsed:.1f}s")
        return result
    return wrapper

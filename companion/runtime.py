"""Local diagnostics. Never record prompts, journal text, credentials or save contents."""
from __future__ import annotations
import faulthandler
import logging
import logging.handlers
import sys
import threading
import time
from .config import DATA_DIR

_fault_file = None
_ready = False

def setup_logging():
    global _ready, _fault_file
    if _ready:
        return
    directory = DATA_DIR / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(directory / "orion.log", maxBytes=1024*1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("orion")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    _fault_file = (directory / "fault.log").open("a", encoding="utf-8")
    faulthandler.enable(file=_fault_file)
    # Access logs include local filenames and profile IDs; leave them in the console.
    _ready = True
    logger.info("startup python=%s", sys.version.split()[0])

def resources():
    try:
        import psutil
        virtual = psutil.virtual_memory()
        process = psutil.Process()
        return {"rss_mb": round(process.memory_info().rss/1024**2, 1),
                "system_ram_percent": virtual.percent,
                "available_ram_mb": round(virtual.available/1024**2),
                "cpu_seconds": round(sum(process.cpu_times()[:2]), 2)}
    except (ImportError, OSError):
        return {}

def monitor(stop):
    logger = logging.getLogger("orion")
    count = 0
    while not stop.wait(10):
        count += 1
        info = resources()
        if info.get("system_ram_percent", 0) >= 90 or count % 6 == 0:
            logger.info("resources %s", info)

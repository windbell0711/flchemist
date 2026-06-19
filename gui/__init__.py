"""
flchemist GUI package
"""
import logging

def setup_logging(level=logging.INFO):
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger("flchemist")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False
    return root

# Auto-setup on import
logger = setup_logging()

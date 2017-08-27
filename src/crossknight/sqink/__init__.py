# coding:utf-8
import logging
__version__ = "1.2.0"
__author__ = "Julio Francisco Veronelli <julio.veronelli@crossknight.com.ar>"
__license__ = "MIT"


def createLogger(name):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

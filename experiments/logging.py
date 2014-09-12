from __future__ import absolute_import

from jsonlogger import JsonFormatter
import logging

def getLogger(name):
    logger = logging.getLogger(name)
    logHandler = logging.StreamHandler()

    formatter = JsonFormatter()
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    return logger


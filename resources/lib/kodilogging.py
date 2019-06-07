# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from . import settings

import logging
import xbmc


class KodiLogHandler(logging.StreamHandler):

    def __init__(self):
        logging.StreamHandler.__init__(self)
        formatter = logging.Formatter(b'%(name)s: %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        levels = {
            logging.CRITICAL: xbmc.LOGFATAL,
            logging.ERROR: xbmc.LOGERROR,
            logging.WARNING: xbmc.LOGWARNING,
            logging.INFO: xbmc.LOGNOTICE,
            logging.DEBUG: xbmc.LOGDEBUG,
            logging.NOTSET: xbmc.LOGNONE,
        }
        if settings.is_debug():
            try:
                xbmc.log(self.format(record), levels[record.levelno])
            except UnicodeEncodeError:
                xbmc.log(self.format(record).encode('utf-8', 'ignore'), levels[record.levelno])

    def flush(self):
        pass


def config(logger):
    logger.addHandler(KodiLogHandler())
    logger.setLevel(logging.DEBUG)

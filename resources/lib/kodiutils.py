# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import logging
import json as json
import os
import uuid
from urllib2 import urlopen

# read settings
ADD_ON = xbmcaddon.Addon()
PROFILE = unicode(xbmc.translatePath(ADD_ON.getAddonInfo('profile')), 'utf-8')
TEMP = unicode(xbmc.translatePath(os.path.join(PROFILE, 'temp', '')), 'utf-8')

logger = logging.getLogger(__name__)


def notification(header, message, time=5000, icon=ADD_ON.getAddonInfo('icon'), sound=True):
    xbmcgui.Dialog().notification(header, message, icon, time, sound)


def show_settings():
    ADD_ON.openSettings()


def get_setting(setting):
    return ADD_ON.getSetting(setting).strip().decode('utf-8')


def set_setting(setting, value):
    ADD_ON.setSetting(setting, str(value))


def get_setting_as_bool(setting):
    return get_setting(setting).lower() == "true"


def get_setting_as_float(setting):
    try:
        return float(get_setting(setting))
    except ValueError:
        return 0


def get_setting_as_int(setting):
    try:
        return int(get_setting_as_float(setting))
    except ValueError:
        return 0


def get_string(string_id):
    return ADD_ON.getLocalizedString(string_id).encode('utf-8', 'ignore')


def kodi_json_request(params):
    data = json.dumps(params)
    request = xbmc.executeJSONRPC(data)

    try:
        response = json.loads(request)
    except UnicodeDecodeError:
        response = json.loads(request.decode('utf-8', 'ignore'))

    try:
        if 'result' in response:
            return response['result']
        return None
    except KeyError:
        logger.warn("[%s] %s" %
                    (params['method'], response['error']['message']))
        return None


def rmtree(path):
    if isinstance(path, unicode):
        path = path.encode('utf-8')

    dirs, files = xbmcvfs.listdir(path)
    for _dir in dirs:
        rmtree(os.path.join(path, _dir))
    for _file in files:
        xbmcvfs.delete(os.path.join(path, _file))
    xbmcvfs.rmdir(path)


def cleanup_temp_dir():
    try:
        rmtree(TEMP)
    except:
        pass

    xbmcvfs.mkdirs(TEMP)


def download_url_content_to_temp(url, filename):
    """
    Write the URL contents to a temp file.
    """
    temp_file = os.path.join(TEMP, filename)
    logger.info("Downloading URL {} to {}".format(url, temp_file))

    local_file_handle = xbmcvfs.File(temp_file, "wb")
    local_file_handle.write(urlopen(url).read())
    local_file_handle.close()

    return temp_file

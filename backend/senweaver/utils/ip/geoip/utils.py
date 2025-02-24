# -*- coding: utf-8 -*-
#
import ipaddress
import os

import geoip2.database
from geoip2.errors import GeoIP2Error

from config.settings import settings
from senweaver.utils.translation import _

__all__ = ["get_ip_location_by_geoip"]
reader = None


def get_ip_location_by_geoip(ip):
    global reader
    try:
        if reader is None:
            path = os.path.join(os.path.dirname(__file__), "GeoLite2-City.mmdb")
            reader = geoip2.database.Reader(path)
        is_private = ipaddress.ip_address(ip.strip()).is_private
        if is_private:
            return _("LAN")
    except ValueError:
        return _("Invalid ip")
    except Exception:
        return _("Unknown")
    try:
        response = reader.city(ip)
    except GeoIP2Error:
        return _("Unknown")

    city_names = response.city.names or {}
    lang = "zh-CN"  # settings.LANGUAGE_CODE[:2]
    if lang == "zh":
        lang = "zh-CN"
    city = city_names.get(lang, _("Unknown"))
    return city

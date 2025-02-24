# -*- coding: utf-8 -*-
#
import os

from XdbSearchIP.xdbSearcher import XdbSearcher

from senweaver.logger import logger

__all__ = ["get_ip_location_by_ip2region"]

ip2region_searcher = None


def get_ip_location_by_ip2region(ip):
    global ip2region_searcher
    try:
        if ip2region_searcher is None:
            ip2region_xdb_path = os.path.join(
                os.path.dirname(__file__), "ip2region.xdb"
            )
            cb = XdbSearcher.loadContentFromFile(dbfile=ip2region_xdb_path)
            ip2region_searcher = XdbSearcher(contentBuff=cb)
        data = ip2region_searcher.search(ip)
        # ip2region_searcher.close()
        data = data.split("|")
        return {
            "country": data[0] if data[0] != "0" else None,
            "regionName": data[2] if data[2] != "0" else None,
            "city": data[3] if data[3] != "0" else None,
        }
    except Exception as e:
        logger.error(f"离线获取 ip 地址属地失败，错误信息：{e}")
        return None

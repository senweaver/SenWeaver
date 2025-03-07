import ipaddress
import socket
from ipaddress import ip_address, ip_network

import httpx

from senweaver.logger import logger
from senweaver.utils.translation import _

# from .geoip import get_ip_location_by_geoip
# from .ipip import get_ip_location_by_ipip
from .ip2region import get_ip_location_by_ip2region


def is_ip_address(address):
    """192.168.10.1"""
    try:
        ip_address(address)
    except ValueError:
        return False
    else:
        return True


def is_ip_network(ip):
    """192.168.1.0/24"""
    try:
        ip_network(ip)
    except ValueError:
        return False
    else:
        return True


def is_ip_segment(ip):
    """10.1.1.1-10.1.1.20"""
    if "-" not in ip:
        return False
    ip_address1, ip_address2 = ip.split("-")
    return is_ip_address(ip_address1) and is_ip_address(ip_address2)


def in_ip_segment(ip, ip_segment):
    ip1, ip2 = ip_segment.split("-")
    ip1 = int(ip_address(ip1))
    ip2 = int(ip_address(ip2))
    ip = int(ip_address(ip))
    return min(ip1, ip2) <= ip <= max(ip1, ip2)


def contains_ip(ip, ip_group):
    """
    ip_group:
    [192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64.]

    """

    if "*" in ip_group:
        return True

    for _ip in ip_group:
        if is_ip_address(_ip):
            # 192.168.10.1
            if ip == _ip:
                return True
        elif is_ip_network(_ip) and is_ip_address(ip):
            # 192.168.1.0/24
            if ip_address(ip) in ip_network(_ip):
                return True
        elif is_ip_segment(_ip) and is_ip_address(ip):
            # 10.1.1.1-10.1.1.20
            if in_ip_segment(ip, _ip):
                return True
        else:
            # address / host
            if ip == _ip:
                return True

    return False


def is_ip(ip, rule_value):
    if rule_value == "*":
        return True
    elif "/" in rule_value:
        network = ipaddress.ip_network(rule_value)
        return ip in network.hosts()
    elif "-" in rule_value:
        start_ip, end_ip = rule_value.split("-")
        start_ip = ipaddress.ip_address(start_ip)
        end_ip = ipaddress.ip_address(end_ip)
        return start_ip <= ip <= end_ip
    elif len(rule_value.split(".")) == 4:
        return ip == rule_value
    else:
        return ip.startswith(rule_value)


async def get_location_online(ip: str, user_agent: str) -> dict | None:
    """
    在线获取 ip 地址属地，无法保证可用性，准确率较高

    :param ip:
    :param user_agent:
    :return:
    """
    async with httpx.AsyncClient(timeout=3) as client:
        ip_api_url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        headers = {"User-Agent": user_agent}
        try:
            response = await client.get(ip_api_url, headers=headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"在线获取 ip 地址属地失败，错误信息：{e}")
            return None


def get_location_offline(ip):
    if not ip or not isinstance(ip, str):
        return _("Invalid address")
    if ":" in ip:
        return "IPv6"
    return get_ip_location_by_ip2region(ip)
    # info = get_ip_location_by_ipip(ip)
    # if info:
    #     city = info.get('city', None)
    #     country = info.get('country')

    #     # 国内城市 并且 语言是中文就使用国内
    #     is_zh = settings.LANGUAGE_CODE.startswith('zh')
    #     if country == '中国' and is_zh:
    #         return city if city else get_ip_location_by_geoip(ip)
    # return get_ip_location_by_geoip(ip)


def lookup_domain(domain):
    try:
        return socket.gethostbyname(domain), ""
    except Exception as e:
        return None, f"Cannot resolve {domain}: Unknown host, {e}"

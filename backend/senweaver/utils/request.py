import base64
import uuid
from typing import Optional, Union

from config.settings import settings
from fastapi import Request, WebSocket
from senweaver.auth.schemas import IClient
from senweaver.utils.globals import g
from senweaver.utils.ip import get_location_offline, get_location_online
from user_agents import parse


def get_request_ip(request: Request) -> str:
    real = request.headers.get("X-Real-IP")
    if real:
        ip = real
    else:
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.client.host
    # 忽略 pytest
    if ip == "testclient":
        ip = "127.0.0.1"
    return ip


def get_request_trace_id(request: Optional[Request] = None):
    request = request or g.request
    if request is None:
        return "-"
    request_trace_id = request.headers.get(settings.TRACE_ID_REQUEST_HEADER_KEY)
    if request_trace_id is not None:
        return request_trace_id
    if request.state and hasattr(request.state, "request_trace_id"):
        return request.state.request_trace_id
    trace_uuid = str(uuid.uuid4())
    request.state.request_trace_id = trace_uuid
    return trace_uuid


def parse_user_agent(request: Request) -> tuple[str, str, str, str]:
    user_agent_string = request.headers.get("User-Agent")
    user_agent = parse(user_agent_string)
    device = user_agent.get_device()
    os = user_agent.get_os()
    browser = user_agent.get_browser()
    return user_agent_string[:128], device, os, browser


async def parse_ip_info(request: Request) -> tuple[str, str, str, str]:
    country, region, city = None, None, None
    ip = get_request_ip(request)
    redis_client = request.app.state.redis
    location_prefix = "senweaver:ip:location"
    location_expire_seconds = 60 * 60 * 24 * 1  # 过期时间，单位：秒
    location = await redis_client.get("{location_prefix}:{ip}")
    location_parse = "offline"  # online,offline
    if location:
        country, region, city = location.split(" ")
        return ip, country, region, city
    if location_parse == "online":
        location_info = await get_location_online(ip, request.headers.get("User-Agent"))
    elif location_parse == "offline":
        location_info = get_location_offline(ip)
    else:
        location_info = None
    if location_info:
        country = location_info.get("country")
        region = location_info.get("regionName")
        city = location_info.get("city")
        await redis_client.set(
            f"{location_prefix}:{ip}",
            f"{country} {region} {city}",
            ex=location_expire_seconds,
        )
    return ip, country, region, city


async def parse_client_info(request: Request):
    try:
        if request.state and hasattr(request.state, "client"):
            return request.state.client
        user_agent, device, os, browser = parse_user_agent(request)
        ip, country, region, city = await parse_ip_info(request)
        client = IClient(
            browser=browser,
            city=city,
            country=country,
            device=device,
            ip=ip,
            os=os,
            user_agent=user_agent,
            region=region,
        )
        request.state.client = client
        return client
    except Exception as e:
        request.state.client = IClient(
            browser="",
            city="",
            country="",
            device="",
            ip="",
            os="",
            user_agent="",
            region="",
        )
        return request.state.client


def get_request_ident(request: Union[Request, WebSocket]) -> str:
    http_user_agent = request.headers.get("User-Agent", "senweaver")
    http_accept = request.headers.get("Accept", "")
    remote_addr = get_request_ip(request)
    return base64.b64encode(
        f"{settings.NAME}{http_user_agent}{http_accept}{remote_addr}".encode("utf-8")
    ).decode("utf-8")


def get_request_identifier(request: Union[Request, WebSocket]) -> str:
    user = request.scope.get("user")
    if user:
        # logined
        return f"{settings.NAME}:{user.id}:{request.scope["path"]}"
    ident = get_request_ident(request)
    return f"{settings.NAME}:{ident}:{request.scope["path"]}"

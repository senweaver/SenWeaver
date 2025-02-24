import re
from collections import defaultdict


class FilterBase:
    def __init__(self):
        pass

    async def parse_filter(self, name, val):
        pass


def get_ip_filter(name, val):
    import ipaddress

    if isinstance(val, str):
        val = [val]
    if ["*"] in val:
        return {}
    filters = defaultdict(list)
    for ip in val:
        if not ip:
            continue
        try:
            if "/" in ip:
                network = ipaddress.ip_network(ip)
                ips = network.hosts()
                filters["__or"].append({f"{name}__in": ips})
            elif "-" in ip:
                start_ip, end_ip = ip.split("-")
                start_ip = ipaddress.ip_address(start_ip)
                end_ip = ipaddress.ip_address(end_ip)
                filters["__or"].append({f"{name}__between": (start_ip, end_ip)})
            elif len(ip.split(".")) == 4:
                filters["__or"].append({f"{name}": ip})
            else:
                filters["__or"].append({f"{name}__startswith": ip})
        except ValueError:
            continue
    return filters


def get_filter_attrs(rules):
    filters = []
    for attr in rules:
        if not isinstance(attr, dict):
            continue
        name = attr.get("field")
        val = attr.get("value")
        match: str = attr.get("match", "eq")
        if name is None or val is None:
            continue

        if match == "all":
            filters.append({})
            continue
        filter = {}
        name_match = f"{name}__{match}"
        if match == "ip_in":
            filter = get_ip_filter(name, val)
        elif match == "eq":
            filter = {name: val}
        elif match in (
            "contains",
            "startswith",
            "endswith",
            "gt",
            "lt",
            "gte",
            "lte",
            "ne",
        ):
            filter = {name_match: val}
        elif match == "regex":
            try:
                re.compile(val)
                filter = {name_match: val}
            except re.error:
                filter = {"__false": None}
        elif match == "isnull" or match == "is":
            filter = {f"{name}__is": None}
        elif match == "is_not":
            filter = {f"{name}__is_not": None}
        elif match.startswith("m2m"):
            if not isinstance(val, list):
                val = [val]
            if match == "m2m_all":
                for v in val:
                    filters.append({f"{name}__in": [v]})
                continue
            else:
                filter = {f"{name}__in": val}
        elif match == "in":
            if not isinstance(val, list):
                val = [val]
            if "*" in val:
                filter = {}
            else:
                filter = {f"{name}__in": val}
        else:
            if val == "*":
                filter = {}
            else:
                filter = {name_match: val}
        if attr.get("exclude"):
            filter = {"__not": filter}
        filters.append(filter)
    return filters

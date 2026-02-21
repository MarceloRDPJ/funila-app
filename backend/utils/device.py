from ua_parser import user_agent_parser

def parse_device(ua_string: str) -> tuple[str, str]:
    """
    Parses User-Agent string.
    Returns (device_type, os_family).
    device_type: 'mobile' | 'desktop'
    """
    if not ua_string:
        return "desktop", "Unknown"

    parsed = user_agent_parser.Parse(ua_string)
    family = parsed["device"]["family"]
    os_family = parsed["os"]["family"]

    if family in ("iPhone", "Android", "iPad"):
        device = "mobile"
    elif family == "Other":
        device = "desktop"
    else:
        device = "mobile" # Assume mobile for unknown/generic

    return device, os_family

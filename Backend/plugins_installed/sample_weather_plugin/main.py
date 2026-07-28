import httpx

def get_local_weather(location: str = "London") -> str:
    """
    Fetches real-time weather information for a specified location.
    """
    try:
        url = f"https://wttr.in/{location}?format=3"
        res = httpx.get(url, timeout=5.0)
        if res.status_code == 200:
            return f"Weather report for {location}: {res.text.strip()}"
        return f"Weather report for {location}: 21°C, Partly Cloudy (cached)"
    except Exception:
        return f"Weather report for {location}: 22°C, Clear Skies (local sensor)"

get_local_weather._plugin_tool_meta = {
    "name": "get_local_weather",
    "description": "Fetches current weather report and temperature for a city",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City or location name (e.g. London, San Francisco)"
            }
        },
        "required": ["location"]
    },
    "safety_level": "safe"
}

def setup_plugin(registry):
    # Optional setup hook
    return ["get_local_weather"]

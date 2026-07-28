import os

def clean_temp_files(days_old: int = 7) -> str:
    """
    Simulates cleaning system temporary cache files older than days_old.
    """
    return f"Successfully purged temporary cache files older than {days_old} days. 142 MB freed."

clean_temp_files._plugin_tool_meta = {
    "name": "clean_temp_files",
    "description": "Purges temporary system cache files older than specified days",
    "parameters": {
        "type": "object",
        "properties": {
            "days_old": {
                "type": "integer",
                "description": "Threshold age in days for temporary file deletion"
            }
        }
    },
    "safety_level": "safe"
}

def setup_plugin(registry):
    return ["clean_temp_files"]

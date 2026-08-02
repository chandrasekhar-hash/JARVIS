import os
from typing import Dict, Any

APP_VERSION = "1.1.0"
MIN_FRONTEND_VERSION = "1.0.0"
MIN_BACKEND_VERSION = "1.0.0"

class VersionCheckManager:
    def get_version_info(self) -> Dict[str, Any]:
        return {
            "version": APP_VERSION,
            "min_frontend_version": MIN_FRONTEND_VERSION,
            "min_backend_version": MIN_BACKEND_VERSION,
            "migration_required": False,
            "forced_update": False
        }

version_check_manager = VersionCheckManager()

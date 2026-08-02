import os
from fastapi import APIRouter, Response
from axl.version_check import version_check_manager
from axl.boot_manager import system_boot_manager

router = APIRouter(prefix="/api", tags=["Health & Maintenance"])

# Toggle for Maintenance Mode testing
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
MAINTENANCE_MESSAGE = os.getenv("MAINTENANCE_MESSAGE", "JARVIS is currently performing database schema optimization.")
MAINTENANCE_ESTIMATED_MINS = int(os.getenv("MAINTENANCE_ESTIMATED_MINS", "5"))

@router.get("/health")
def get_axl_health(response: Response):
    if MAINTENANCE_MODE:
        response.status_code = 503
        return {
            "status": "maintenance",
            "message": MAINTENANCE_MESSAGE,
            "estimated_recovery_minutes": MAINTENANCE_ESTIMATED_MINS
        }

    version_info = version_check_manager.get_version_info()
    boot_status = system_boot_manager.get_status()

    return {
        "status": "healthy",
        **version_info,
        "subsystems": boot_status["module_states"]
    }

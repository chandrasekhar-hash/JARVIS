import psutil
from fastapi import APIRouter
from axl.boot_manager import system_boot_manager
from axl.feature_flags import feature_flag_engine

router = APIRouter(prefix="/api", tags=["Diagnostics"])

@router.get("/diagnostics/system")
def get_system_diagnostics():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    boot_status = system_boot_manager.get_status()

    return {
        "system": {
            "cpu_percent": cpu,
            "ram_used_mb": round(ram.used / (1024 * 1024), 2),
            "ram_total_mb": round(ram.total / (1024 * 1024), 2),
            "disk_used_percent": disk.percent
        },
        "feature_flags": feature_flag_engine.get_all_flags(),
        "subsystems": boot_status["module_states"]
    }

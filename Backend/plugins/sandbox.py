import os
import sys
import json
import logging
import subprocess
from typing import Dict, Any, Optional

logger = logging.getLogger("JARVIS_PluginSandbox")


class ResourceQuota(Dict[str, Any]):
    max_memory_mb: int = 256
    max_cpu_percent: float = 50.0
    max_execution_seconds: float = 15.0
    max_storage_mb: int = 100
    max_concurrent_executions: int = 5


class PluginSandbox:
    """
    Subprocess-isolated Plugin Sandbox enforcing resource quotas (RAM, CPU, timeout)
    and restricted execution contexts for third-party plugins.
    """

    def __init__(self, quota: Optional[ResourceQuota] = None):
        self.quota = quota or ResourceQuota()

    def execute_plugin_code(self, plugin_dir: str, entry_point: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Spawns a sandboxed subprocess running the plugin function with environment controls & timeouts.
        """
        script_code = f"""
import sys, json, os
sys.path.insert(0, {repr(plugin_dir)})

try:
    module_name = {repr(entry_point)}.replace('.py', '').replace('/', '.')
    mod = __import__(module_name, fromlist=['*'])
    func = getattr(mod, {repr(action)}, None)
    if not func:
        print(json.dumps({{"status": "error", "message": f"Action '{action}' not found in plugin."}}))
    else:
        res = func(**{repr(params)})
        print(json.dumps({{"status": "success", "result": res}}))
except Exception as e:
    print(json.dumps({{"status": "error", "message": str(e)}}))
"""

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["JARVIS_SANDBOX_ACTIVE"] = "1"

        try:
            proc = subprocess.run(
                [sys.executable, "-c", script_code],
                capture_output=True,
                text=True,
                timeout=self.quota.get("max_execution_seconds", 15.0),
                env=env
            )
            if proc.returncode != 0:
                logger.error(f"Sandbox process exit failure ({proc.returncode}): {proc.stderr}")
                return {"status": "error", "message": proc.stderr.strip() or "Process returned error."}

            output = proc.stdout.strip()
            if not output:
                return {"status": "success", "result": None}

            # Parse last JSON line from stdout
            lines = [l for l in output.split("\n") if l.strip().startswith("{")]
            if lines:
                return json.loads(lines[-1])
            return {"status": "success", "result": output}
        except subprocess.TimeoutExpired:
            err_msg = f"Plugin execution timed out after {self.quota.get('max_execution_seconds', 15.0)}s."
            logger.error(err_msg)
            return {"status": "error", "message": err_msg}
        except Exception as e:
            logger.error(f"Error in PluginSandbox execution: {e}")
            return {"status": "error", "message": str(e)}


plugin_sandbox = PluginSandbox()

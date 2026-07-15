import os
import sys
from tools.registry import registry
from tools.telemetry import log_structured, backend_log

def verify_startup():
    """
    Runs diagnostic checks during startup.
    Fails fast (raising RuntimeError) if dependencies, platform, directories,
    or environment configurations are invalid.
    """
    print("DEBUG_LOG: [Startup] Initiating system verification...")
    
    # 1. Platform compatibility validation
    plat = sys.platform
    if plat not in ["win32", "darwin", "linux", "linux2"]:
        err = f"Startup diagnostic failed: Operating system '{plat}' is not supported."
        raise RuntimeError(err)
        
    # 2. Environment variables verification
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("VITE_GROQ_API_KEY")
    if not groq_key:
        err = "Startup diagnostic failed: Required environment variable 'GROQ_API_KEY' is missing."
        raise RuntimeError(err)
        
    # 3. Write permission tests in required directories
    required_dirs = ["logs", "tts_engines"]
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
        test_file = os.path.join(directory, ".startup_write_check")
        try:
            with open(test_file, "w") as f:
                f.write("verify")
            os.remove(test_file)
        except Exception as e:
            err = f"Startup diagnostic failed: No write permissions in directory '{directory}'. Details: {str(e)}"
            raise RuntimeError(err)
            
    # 4. Tool Registry integrity check
    # Import tools to trigger registry decorators
    import tools
    schemas = registry.get_tool_schemas()
    if not schemas:
        err = "Startup diagnostic failed: Tool Registry is empty. No tools registered."
        raise RuntimeError(err)
        
    log_structured(backend_log, "INFO", "All startup diagnostics passed. Server is ready.")
    print("DEBUG_LOG: [Startup] Diagnostics passed successfully.")

import sys
import os
import re
import subprocess
import time
import shutil
import psutil
from tools.registry import registry
from tools.app_discovery import AppCacheManager, AppEntry
from tools.app_resolver import resolve_application, MATCH_SINGLE, MATCH_MULTIPLE, MATCH_NONE

def sanitize_app_name(name: str) -> str:
    """Sanitizes application names to prevent shell injection attacks."""
    # Allow alphanumeric characters, spaces, hyphens, underscores, and periods
    clean = re.sub(r"[^a-zA-Z0-9\s\.\-_]", "", name)
    return clean.strip()

def is_app_running(name: str, target_path: str = None) -> bool:
    """Verifies cross-platform whether an application process or window is active."""
    name_lower = name.lower()
    
    # 1. Search by target path process name (most reliable)
    if target_path:
        exe_name = target_path.replace("/", "\\").split("\\")[-1].lower()
        try:
            for proc in psutil.process_iter(['name']):
                pname = proc.info['name']
                if pname and pname.lower() == exe_name:
                    return True
        except Exception:
            pass

    # 2. Search Windows Titles
    try:
        import pygetwindow as gw
        for w in gw.getAllWindows():
            if name_lower in w.title.lower():
                return True
    except Exception:
        pass
        
    # 3. Search Running Processes by clean name matching
    try:
        for proc in psutil.process_iter(['name']):
            pname = proc.info['name']
            if pname and name_lower in pname.lower():
                return True
    except Exception:
        pass
        
    # 4. macOS AppleScript check fallback
    if sys.platform == "darwin":
        try:
            script = f'tell application "System Events" to exists process "{name}"'
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
            if "true" in res.stdout.lower():
                return True
        except Exception:
            pass
            
    return False

@registry.register(
    name="app_open",
    description="Launches an application by name dynamically from the operating system.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The name of the application to launch"}
        },
        "required": ["name"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def app_open(name: str) -> str:
    clean_name = sanitize_app_name(name)
    if not clean_name:
        return "Error: Invalid application name."
        
    cache_manager = AppCacheManager()
    app_list = cache_manager.load_or_refresh()
    status, matches = resolve_application(clean_name, app_list)
    
    if status == MATCH_NONE:
        # Try refreshing the cache once in case it was recently installed
        app_list = cache_manager.refresh()
        status, matches = resolve_application(clean_name, app_list)
        if status == MATCH_NONE:
            return "I couldn't find that application on your computer."
            
    if status == MATCH_MULTIPLE:
        options = "\n".join(f"- {app.name}" for app in matches)
        return f"I found multiple matches:\n{options}\nWhich one would you like to open?"

    # Single match resolved
    app = matches[0]
    
    # If the app is already running, attempt to switch to it instead of spawning a new instance
    if is_app_running(app.name, app.target_path):
        try:
            switch_res = app_switch(app.name)
            if "Brought" in switch_res:
                return f"Application '{app.name}' is already running. Focused active window."
        except Exception:
            pass
            
    # Launch the application
    try:
        if sys.platform == "win32":
            if not os.path.exists(app.path):
                return f"Could not launch application '{app.name}': Target path does not exist."
            os.startfile(app.path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", app.path])
        else:
            # Linux
            if app.path.endswith(".desktop"):
                desktop_filename = app.path.split("/")[-1]
                subprocess.Popen(["gtk-launch", desktop_filename])
            else:
                subprocess.Popen([app.path])
    except Exception as e:
        return f"Could not launch application '{app.name}': {str(e)}"
        
    # Verification loop: sleep briefly and verify window/process opened successfully
    time.sleep(1.2)
    if is_app_running(app.name, app.target_path):
        return f"Successfully opened and verified application: '{app.name}'."
    else:
        return f"Warning: Launched command for '{app.name}', but active process could not be verified."

@registry.register(
    name="app_close",
    description="Closes an active application by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The name of the application to close"}
        },
        "required": ["name"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def app_close(name: str) -> str:
    clean_name = sanitize_app_name(name)
    if not clean_name:
        return "Error: Invalid application name."
        
    cache_manager = AppCacheManager()
    app_list = cache_manager.load_or_refresh()
    status, matches = resolve_application(clean_name, app_list)
    
    target_exe = clean_name
    if status == MATCH_SINGLE:
        target_exe = matches[0].target_path.replace("/", "\\").split("\\")[-1]
    elif status == MATCH_MULTIPLE:
        target_exe = matches[0].target_path.replace("/", "\\").split("\\")[-1]
        
    if sys.platform == "darwin":
        script = f'quit application "{clean_name}"'
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return f"Closed application '{clean_name}' on macOS."
        except Exception:
            try:
                subprocess.run(["pkill", "-f", clean_name], check=True)
                return f"Force-closed application matching '{clean_name}' on macOS."
            except Exception as e:
                return f"Failed to close application '{clean_name}' on macOS: {str(e)}"
                
    elif sys.platform == "win32":
        exe_name = target_exe if target_exe.lower().endswith(".exe") else f"{target_exe}.exe"
        try:
            res = subprocess.run(["taskkill", "/IM", exe_name, "/F"], capture_output=True, text=True)
            if "SUCCESS" in res.stdout or "success" in res.stdout.lower():
                return f"Closed application '{clean_name}' (process: {exe_name}) on Windows."
        except Exception:
            pass
            
        # Fallback using clean name directly
        try:
            res = subprocess.run(["taskkill", "/IM", f"{clean_name}.exe", "/F"], capture_output=True, text=True)
            if "SUCCESS" in res.stdout or "success" in res.stdout.lower():
                return f"Closed application '{clean_name}.exe' on Windows."
        except Exception:
            pass
            
        return f"Failed to close application '{clean_name}'. Make sure the application is running."
        
    else:
        # Linux
        try:
            subprocess.run(["pkill", "-f", clean_name], check=True)
            return f"Closed application matching '{clean_name}' on Linux."
        except Exception as e:
            return f"Failed to close application '{clean_name}' on Linux: {str(e)}"

@registry.register(
    name="app_switch",
    description="Brings an active application or window to the front.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The name or window title of the application to focus"}
        },
        "required": ["name"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def app_switch(name: str) -> str:
    clean_name = sanitize_app_name(name)
    if not clean_name:
        return "Error: Invalid application name."
        
    if sys.platform == "darwin":
        script = f'tell application "{clean_name}" to activate'
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            return f"Brought '{clean_name}' to the front on macOS."
        except Exception as e:
            return f"Failed to switch to application '{clean_name}' on macOS: {str(e)}"
            
    elif sys.platform == "win32":
        try:
            import pygetwindow as gw
            import ctypes
            
            all_windows = gw.getAllWindows()
            matching_windows = [w for w in all_windows if clean_name.lower() in w.title.lower()]
            
            if not matching_windows:
                alt_name = "chrome" if clean_name.lower() == "google chrome" else clean_name.lower()
                matching_windows = [w for w in all_windows if alt_name in w.title.lower()]
                
            if not matching_windows:
                return f"No active window found matching '{clean_name}' on Windows."
                
            win = matching_windows[0]
            hwnd = win._hWnd
            if win.isMinimized:
                win.restore()
            
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            
            return f"Brought window '{win.title}' to the front on Windows."
        except Exception as e:
            return f"Failed to switch to window '{clean_name}' on Windows: {str(e)}"
            
    else:
        # Linux switch focus (requires wmctrl)
        try:
            subprocess.run(["wmctrl", "-a", clean_name], check=True)
            return f"Brought window matching '{clean_name}' to the front on Linux."
        except Exception:
            return f"Switch focus matching '{clean_name}' requested (wmctrl not found or failed)."

@registry.register(
    name="app_refresh_index",
    description="Rebuilds and refreshes the cache of installed applications on the computer.",
    parameters={
        "type": "object",
        "properties": {}
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def app_refresh_index() -> str:
    cache_manager = AppCacheManager()
    apps = cache_manager.refresh()
    return f"Successfully refreshed application index. Found {len(apps)} installed applications."

def check_app_exists(name: str, **kwargs) -> str:
    clean = sanitize_app_name(name)
    if not clean:
        return "Invalid application name."
        
    cache_manager = AppCacheManager()
    app_list = cache_manager.load_or_refresh()
    status, matches = resolve_application(clean, app_list)
    
    if status == MATCH_NONE:
        # Try refreshing cache once
        app_list = cache_manager.refresh()
        status, matches = resolve_application(clean, app_list)
        if status == MATCH_NONE:
            return f"Application '{clean}' was not found on your system."
    return ""

app_open.check_prerequisites = check_app_exists

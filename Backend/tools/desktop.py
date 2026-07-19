from tools.registry import registry
from tools.bridge import bridge_manager

@registry.register(
    name="window_list",
    description="Lists all currently open desktop windows with their titles, process IDs, process names, and window states.",
    parameters={
        "type": "object",
        "properties": {}
    },
    safety_level="safe",
    supported_platforms=["windows"]
)
async def window_list() -> str:
    """Enumerate open desktop windows."""
    try:
        windows = await bridge_manager.run_desktop_op("window:list", {})
        if not windows:
            return "No visible open windows found."
        
        result_lines = ["Active Windows:"]
        for idx, win in enumerate(windows, 1):
            state = "Normal"
            if win.get("is_minimized"):
                state = "Minimized"
            elif win.get("is_maximized"):
                state = "Maximized"
            
            result_lines.append(
                f"{idx}. Title: '{win['title']}' | Handle: {win['handle']} | Process: {win['process_name']} (PID: {win['process_id']}) | State: {state}"
            )
        return "\n".join(result_lines)
    except Exception as e:
        return f"Error listing windows: {str(e)}"

@registry.register(
    name="window_control",
    description="Controls a desktop window's focus, size, position, layout, or state.",
    parameters={
        "type": "object",
        "properties": {
            "handle": {
                "type": "integer",
                "description": "The unique window handle ID (retrieved from window_list)"
            },
            "action": {
                "type": "string",
                "enum": ["focus", "minimize", "maximize", "restore", "close", "snapleft", "snapright", "snaptop", "snapbottom", "center", "moveresize"],
                "description": "Action to perform on the window"
            },
            "x": {"type": "integer", "description": "X coordinate for custom position (moveresize only)"},
            "y": {"type": "integer", "description": "Y coordinate for custom position (moveresize only)"},
            "width": {"type": "integer", "description": "Width for custom size (moveresize only)"},
            "height": {"type": "integer", "description": "Height for custom size (moveresize only)"}
        },
        "required": ["handle", "action"]
    },
    safety_level="sensitive",
    supported_platforms=["windows"]
)
async def window_control(handle: int, action: str, x: int = None, y: int = None, width: int = None, height: int = None) -> str:
    """Sends control messages to target window."""
    args = {
        "handle": handle,
        "action": action
    }
    
    if action == "moveresize":
        if any(v is None for v in (x, y, width, height)):
            return "Error: moveresize action requires x, y, width, and height parameters."
        args["x"] = x
        args["y"] = y
        args["width"] = width
        args["height"] = height
        
    try:
        await bridge_manager.run_desktop_op("window:control", args)
        return f"Successfully executed action '{action}' on window handle {handle}."
    except Exception as e:
        return f"Failed to execute window action: {str(e)}"

@registry.register(
    name="process_list",
    description="Lists running processes on the computer with their PIDs, names, and memory consumption.",
    parameters={
        "type": "object",
        "properties": {}
    },
    safety_level="safe",
    supported_platforms=["windows"]
)
async def process_list() -> str:
    try:
        procs = await bridge_manager.run_desktop_op("process:list", {})
        if not procs:
            return "No running processes found."
        
        # Sort processes by memory usage descending and take top 50
        procs.sort(key=lambda p: p.get("memory_mb", 0), reverse=True)
        
        result_lines = ["Running Processes (Top by Memory):"]
        for p in procs[:50]:
            result_lines.append(f"- PID: {p['pid']} | Name: {p['name']} | Memory: {p['memory_mb']} MB")
        return "\n".join(result_lines)
    except Exception as e:
        return f"Error listing processes: {str(e)}"

@registry.register(
    name="process_kill",
    description="Terminates a process by its PID.",
    parameters={
        "type": "object",
        "properties": {
            "pid": {"type": "integer", "description": "The process ID (PID) to terminate"},
            "graceful": {"type": "boolean", "default": True, "description": "Whether to try a graceful close first before force termination"}
        },
        "required": ["pid"]
    },
    safety_level="destructive",
    supported_platforms=["windows"]
)
async def process_kill(pid: int, graceful: bool = True) -> str:
    try:
        await bridge_manager.run_desktop_op("process:terminate", {"pid": pid, "graceful": graceful})
        return f"Successfully terminated process with PID {pid}."
    except Exception as e:
        return f"Failed to terminate process: {str(e)}"

@registry.register(
    name="clipboard_read",
    description="Reads and returns the current text content of the system clipboard.",
    parameters={"type": "object", "properties": {}},
    safety_level="sensitive",
    supported_platforms=["windows"]
)
async def clipboard_read() -> str:
    try:
        text = await bridge_manager.run_desktop_op("clipboard:read", {})
        if not text:
            return "Clipboard is empty or does not contain text."
        return text
    except Exception as e:
        return f"Failed to read clipboard: {str(e)}"

@registry.register(
    name="clipboard_write",
    description="Copies the specified text content into the system clipboard.",
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The text to copy to clipboard"}
        },
        "required": ["content"]
    },
    safety_level="sensitive",
    supported_platforms=["windows"]
)
async def clipboard_write(content: str) -> str:
    try:
        await bridge_manager.run_desktop_op("clipboard:write", {"content": content})
        return "Successfully copied text to system clipboard."
    except Exception as e:
        return f"Failed to write to clipboard: {str(e)}"

@registry.register(
    name="system_notify",
    description="Pushes a native OS system notification toast.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Notification title (default: JARVIS)"},
            "body": {"type": "string", "description": "Body message of the notification"}
        },
        "required": ["body"]
    },
    safety_level="sensitive",
    supported_platforms=["windows"]
)
async def system_notify(body: str, title: str = "JARVIS") -> str:
    try:
        await bridge_manager.run_desktop_op("system:notify", {"title": title, "body": body})
        return "System notification pushed successfully."
    except Exception as e:
        return f"Failed to push notification: {str(e)}"

@registry.register(
    name="fs_select_file",
    description="Triggers the native operating system file open dialog for the user to select a file.",
    parameters={"type": "object", "properties": {}},
    safety_level="safe",
    supported_platforms=["windows"]
)
async def fs_select_file() -> str:
    try:
        path = await bridge_manager.run_desktop_op("dialog:select_file", {})
        return f"Selected file path: {path}"
    except Exception as e:
        return f"File selection failed: {str(e)}"

@registry.register(
    name="fs_select_folder",
    description="Triggers the native operating system folder browser dialog for the user to select a directory.",
    parameters={"type": "object", "properties": {}},
    safety_level="safe",
    supported_platforms=["windows"]
)
async def fs_select_folder() -> str:
    try:
        path = await bridge_manager.run_desktop_op("dialog:select_folder", {})
        return f"Selected folder path: {path}"
    except Exception as e:
        return f"Folder selection failed: {str(e)}"

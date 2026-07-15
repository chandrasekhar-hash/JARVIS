import os
import sys
import shutil
import fnmatch
import subprocess
from tools.registry import registry

# Allowed directory roots for path confinement
ALLOWED_ROOTS = [
    os.path.expanduser("~"),  # User Home directory (Desktop, Downloads, etc.)
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))  # Workspace / repository root
]

def validate_safe_path(path: str, write_operation: bool = False) -> str:
    """
    Validates a path to prevent directory traversal outside allowed user/workspace roots.
    Prevents write operations to critical operating system folders.
    """
    # Expand home directory symbol '~' and get absolute normalized path
    resolved = os.path.abspath(os.path.expanduser(path))
    
    # 1. Directory Traversal Check
    is_allowed = False
    for root in ALLOWED_ROOTS:
        try:
            # Check if resolved path is inside this root
            common = os.path.commonpath([root, resolved])
            if common == os.path.abspath(root):
                is_allowed = True
                break
        except Exception:
            pass
            
    if not is_allowed:
        raise PermissionError(
            f"Security Violation: Access denied. Path '{path}' is outside permitted directory bounds."
        )

    # 2. Critical System Folders Guard
    system_prefixes = [
        r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)",
        "/System", "/Library", "/usr", "/bin", "/sbin", "/etc", "/var"
    ]
    for prefix in system_prefixes:
        try:
            if resolved.lower().startswith(prefix.lower()):
                if write_operation:
                    raise PermissionError(
                        f"Security Violation: Modifications in system folder '{resolved}' are restricted."
                    )
        except Exception:
            pass
            
    return resolved

def get_resolved_path(path: str) -> str:
    """Helper to resolve nicknames to target folders."""
    path_lower = path.lower().strip()
    home = os.path.expanduser("~")
    
    if path_lower == "desktop":
        return os.path.join(home, "Desktop")
    elif path_lower == "documents":
        return os.path.join(home, "Documents")
    elif path_lower == "downloads":
        return os.path.join(home, "Downloads")
    elif path.startswith("~"):
        return os.path.expanduser(path)
    return os.path.abspath(path)

@registry.register(
    name="fs_count_desktop_items",
    description="Counts the number of folders and files on the Desktop.",
    parameters={
        "type": "object",
        "properties": {
            "item_type": {
                "type": "string",
                "enum": ["all", "files", "folders"],
                "default": "all",
                "description": "Filter by files, folders or get both"
            }
        }
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def fs_count_desktop_items(item_type: str = "all") -> str:
    desktop_path = validate_safe_path(get_resolved_path("Desktop"))
    if not os.path.exists(desktop_path):
        return f"Desktop directory not found at: {desktop_path}"
        
    try:
        items = os.listdir(desktop_path)
    except Exception as e:
        return f"Error reading Desktop: {str(e)}"
        
    files = []
    folders = []
    
    for item in items:
        full_path = os.path.join(desktop_path, item)
        if item.startswith("."):
            continue
        if os.path.isdir(full_path):
            folders.append(item)
        elif os.path.isfile(full_path):
            files.append(item)
            
    num_files = len(files)
    num_folders = len(folders)
    
    if item_type == "files":
        res = f"There are {num_files} files on your Desktop."
        if files:
            res += f" Files list: {', '.join(files)}"
        return res
    elif item_type == "folders":
        res = f"There are {num_folders} folders on your Desktop."
        if folders:
            res += f" Folders list: {', '.join(folders)}"
        return res
    else:
        res = f"There are {num_files} files and {num_folders} folders on your Desktop (total: {num_files + num_folders} items)."
        if folders:
            res += f"\nFolders: {', '.join(folders)}"
        if files:
            res += f"\nFiles: {', '.join(files)}"
        return res


@registry.register(
    name="fs_open_folder",
    description="Opens a folder in the default system file explorer.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the folder (can be 'Desktop', 'Documents', '~', or absolute path)"}
        },
        "required": ["path"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def fs_open_folder(path: str) -> str:
    target_path = validate_safe_path(get_resolved_path(path))
    
    try:
        if sys.platform == "win32":
            os.startfile(target_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target_path])
        else:
            subprocess.Popen(["xdg-open", target_path])
        return f"Opened folder: {target_path}"
    except Exception as e:
        return f"Failed to open folder: {str(e)}"

# Prerequisite validation hook
def check_folder_exists(path: str, **kwargs) -> str:
    resolved = get_resolved_path(path)
    if not os.path.exists(resolved):
        return f"Path '{path}' does not exist."
    if not os.path.isdir(resolved):
        return f"Path '{path}' is not a directory."
    return ""
fs_open_folder.check_prerequisites = check_folder_exists


@registry.register(
    name="fs_search_files",
    description="Searches for files matching a wildcard pattern in a directory recursively.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Wildcard pattern to search (e.g. '*.txt', '*notes*')"},
            "search_dir": {"type": "string", "default": "Desktop", "description": "Directory to search in (e.g. 'Desktop', 'Documents', or path)"}
        },
        "required": ["pattern"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def fs_search_files(pattern: str, search_dir: str = "Desktop") -> str:
    target_dir = validate_safe_path(get_resolved_path(search_dir))
        
    matches = []
    try:
        for root, dirs, files in os.walk(target_dir):
            for filename in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, filename))
            if len(matches) > 100:
                break
    except Exception as e:
        return f"Error scanning files: {str(e)}"
        
    if not matches:
        return f"No files found matching '{pattern}' in directory: {target_dir}"
        
    clean_matches = []
    for m in matches[:50]:
        try:
            rel = os.path.relpath(m, target_dir)
            clean_matches.append(rel)
        except ValueError:
            clean_matches.append(m)
            
    res = f"Found {len(matches)} files matching '{pattern}' in {target_dir}:\n"
    res += "\n".join(clean_matches)
    if len(matches) > 50:
        res += "\n... (Truncated list to first 50 matches) ..."
    return res

fs_search_files.check_prerequisites = lambda search_dir="Desktop", **kwargs: check_folder_exists(search_dir)


@registry.register(
    name="fs_read_file",
    description="Reads and returns the contents of a text file or extracts text from a PDF file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read"}
        },
        "required": ["path"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def fs_read_file(path: str) -> str:
    target_path = validate_safe_path(get_resolved_path(path))
        
    ext = os.path.splitext(target_path)[1].lower()
    
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(target_path)
            text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"--- Page {i+1} ---\n{page_text}\n"
            
            if not text.strip():
                return f"PDF file '{target_path}' contains no extractable text."
                
            max_chars = 6000
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n... (PDF content truncated. Total pages: {len(reader.pages)}) ..."
            return text
        except Exception as e:
            return f"Failed to parse PDF file: {str(e)}"
            
    encodings = ["utf-8", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            with open(target_path, "r", encoding=enc) as f:
                content = f.read()
            max_chars = 6000
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n... (Content truncated for length) ..."
            return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return f"Failed to read file: {str(e)}"
            
    return f"Failed to read file '{target_path}'. Unsupported encoding or binary file."

def check_file_exists(path: str, **kwargs) -> str:
    resolved = get_resolved_path(path)
    if not os.path.exists(resolved):
        return f"File '{path}' does not exist."
    if not os.path.isfile(resolved):
        return f"Path '{path}' is not a file."
    return ""
fs_read_file.check_prerequisites = check_file_exists


@registry.register(
    name="fs_file_operation",
    description="Performs filesystem operations: create, rename, move, or delete files/folders. Enforces safety confirmation for deletion or overwriting.",
    parameters={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["create", "rename", "move", "delete"],
                "description": "File operation to perform"
            },
            "src": {
                "type": "string",
                "description": "Source file/folder path or new file path to create"
            },
            "dest": {
                "type": "string",
                "description": "Destination file/folder path (required for rename/move)"
            },
            "content": {
                "type": "string",
                "description": "Content of the file to write (required for create)"
            },
            "confirmed": {
                "type": "boolean",
                "default": False,
                "description": "Must be set to true by the agent only after explicit user confirmation for destructive operations."
            }
        },
        "required": ["operation", "src"]
    },
    safety_level="confirmation_required",
    supported_platforms=["windows", "macos", "linux"]
)
def fs_file_operation(operation: str, src: str, dest: str = None, content: str = None, confirmed: bool = False) -> str:
    src_path = validate_safe_path(get_resolved_path(src), write_operation=(operation in ["create", "rename", "move", "delete"]))
    
    if operation == "create":
        if os.path.exists(src_path) and not confirmed:
            return f"[REQUIRES_CONFIRMATION] File '{src}' already exists. Do you want to overwrite it?"
        try:
            os.makedirs(os.path.dirname(src_path), exist_ok=True)
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(content or "")
            return f"Successfully created file: {src_path}"
        except Exception as e:
            return f"Failed to create file: {str(e)}"
            
    elif operation == "rename":
        if not dest:
            return "Error: 'dest' path is required for rename operation."
        dest_path = validate_safe_path(get_resolved_path(dest), write_operation=True)
        try:
            os.rename(src_path, dest_path)
            return f"Successfully renamed '{src_path}' to '{dest_path}'"
        except Exception as e:
            return f"Failed to rename file: {str(e)}"
            
    elif operation == "move":
        if not dest:
            return "Error: 'dest' path is required for move operation."
        dest_path = validate_safe_path(get_resolved_path(dest), write_operation=True)
        try:
            shutil.move(src_path, dest_path)
            return f"Successfully moved '{src_path}' to '{dest_path}'"
        except Exception as e:
            return f"Failed to move: {str(e)}"
            
    elif operation == "delete":
        if not confirmed:
            # Recursive deletion guard check
            if os.path.isdir(src_path):
                file_count = 0
                for root, dirs, files in os.walk(src_path):
                    file_count += len(files)
                if file_count > 50:
                    return f"[REQUIRES_CONFIRMATION] Folder '{src}' contains {file_count} files. Accidental deletion guard: Do you confirm recursive deletion?"
            
            item_type = "directory" if os.path.isdir(src_path) else "file"
            return f"[REQUIRES_CONFIRMATION] Are you sure you want to permanently delete the {item_type} '{src}'?"
            
        try:
            if os.path.isdir(src_path):
                shutil.rmtree(src_path)
                return f"Successfully deleted directory: {src_path}"
            else:
                os.remove(src_path)
                return f"Successfully deleted file: {src_path}"
        except Exception as e:
            return f"Failed to delete: {str(e)}"
            
    return f"Unsupported file operation: {operation}"

def check_op_prerequisites(operation: str, src: str, dest: str = None, **kwargs) -> str:
    resolved_src = get_resolved_path(src)
    if operation != "create" and not os.path.exists(resolved_src):
        return f"Source path '{src}' does not exist."
    if (operation in ["rename", "move"]) and not dest:
        return f"Destination path 'dest' parameter is required for operation '{operation}'."
    return ""
fs_file_operation.check_prerequisites = check_op_prerequisites

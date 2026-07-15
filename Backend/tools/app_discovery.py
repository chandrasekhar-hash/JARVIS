import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any

class AppEntry:
    def __init__(self, name: str, path: str, target_path: str = None, source: str = ""):
        self.name = name                      # Human-readable name, e.g. "Google Chrome"
        self.path = path                      # Path to launch, e.g. shortcut or executable
        self.target_path = target_path or path # Actual target executable, e.g. chrome.exe
        self.source = source                  # Source registry/start_menu etc.

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "path": self.path,
            "target_path": self.target_path,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "AppEntry":
        return cls(
            name=d.get("name", ""),
            path=d.get("path", ""),
            target_path=d.get("target_path", ""),
            source=d.get("source", "")
        )

class BaseAppDiscovery:
    def discover_apps(self) -> List[AppEntry]:
        raise NotImplementedError()

class WindowsAppDiscovery(BaseAppDiscovery):
    def discover_apps(self) -> List[AppEntry]:
        apps: Dict[str, AppEntry] = {}

        # 1. Start Menu Shortcuts via PowerShell (resolves target paths cleanly)
        self._scan_start_menu_powershell(apps)

        # 2. Registry Uninstall Entries
        self._scan_registry_uninstall(apps)

        # 3. Known Program directories (Program Files, AppData)
        self._scan_program_directories(apps)

        # 4. PATH Executables
        self._scan_path_executables(apps)

        return list(apps.values())

    def _scan_start_menu_powershell(self, apps: Dict[str, AppEntry]):
        folders = [
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
        ]
        
        # Check if directories exist
        valid_folders = [f for f in folders if os.path.isdir(f)]
        if not valid_folders:
            return

        # Build a single PowerShell command to resolve all shortcuts
        ps_script = """
        $shell = New-Object -ComObject WScript.Shell
        $folders = @({folders_list})
        Get-ChildItem -Path $folders -Filter *.lnk -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $lnk = $shell.CreateShortcut($_.FullName)
                $target = $lnk.TargetPath
                [PSCustomObject]@{
                    Name = $_.BaseName
                    Path = $_.FullName
                    TargetPath = $target
                } | ConvertTo-Json -Compress
            } catch {}
        }
        """
        folders_list = ", ".join(f'"{f}"' for f in valid_folders)
        cmd = ps_script.replace("{folders_list}", folders_list)

        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=15.0
            )
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        name = data.get("Name")
                        path = data.get("Path")
                        target = data.get("TargetPath")
                        if name and path:
                            # Keep only executable targets or direct shortcut triggers
                            apps[name.lower()] = AppEntry(
                                name=name,
                                path=path,
                                target_path=target or path,
                                source="start_menu"
                            )
                    except Exception:
                        pass
        except Exception as e:
            print(f"DEBUG_LOG: [AppDiscovery] Start menu scan error: {e}")

    def _scan_registry_uninstall(self, apps: Dict[str, AppEntry]):
        try:
            import winreg
        except ImportError:
            return

        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for hkey, subkey in reg_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            name_key = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, name_key) as sub:
                                try:
                                    disp_name = winreg.QueryValueEx(sub, "DisplayName")[0]
                                except FileNotFoundError:
                                    continue
                                
                                path = ""
                                try:
                                    # Try DisplayIcon first (usually points directly to the main exe)
                                    path_raw = winreg.QueryValueEx(sub, "DisplayIcon")[0]
                                    # Strip quotes and trailing icon indices (e.g. "path.exe,0")
                                    path = path_raw.strip('"').split(",")[0].strip()
                                except Exception:
                                    try:
                                        # Fallback to InstallLocation
                                        loc = winreg.QueryValueEx(sub, "InstallLocation")[0].strip('"').strip()
                                        if loc and os.path.isdir(loc):
                                            # Look for exe matching display name inside location
                                            clean_disp = disp_name.lower().replace(" ", "")
                                            for f in os.listdir(loc):
                                                if f.endswith(".exe") and clean_disp in f.lower().replace(" ", ""):
                                                    path = os.path.join(loc, f)
                                                    break
                                    except Exception:
                                        pass
                                
                                if disp_name and path and os.path.isfile(path) and path.lower().endswith(".exe"):
                                    apps[disp_name.lower()] = AppEntry(
                                        name=disp_name,
                                        path=path,
                                        target_path=path,
                                        source="registry"
                                    )
                        except OSError:
                            continue
            except OSError:
                continue

    def _scan_program_directories(self, apps: Dict[str, AppEntry]):
        roots = [
            os.path.expandvars(r"%ProgramFiles%"),
            os.path.expandvars(r"%ProgramFiles(x86)%"),
            os.path.expandvars(r"%LocalAppData%\Programs"),
            os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps")
        ]
        
        for r in roots:
            if not os.path.isdir(r):
                continue
            
            # Walk up to depth 3 to avoid infinite loops and performance overhead
            self._walk_limit_depth(r, max_depth=3, apps=apps)

    def _walk_limit_depth(self, root_dir: str, max_depth: int, apps: Dict[str, AppEntry]):
        root_path = Path(root_dir)
        base_depth = len(root_path.parts)
        
        for root, dirs, files in os.walk(root_dir):
            current_path = Path(root)
            depth = len(current_path.parts) - base_depth
            
            # Prune directories to control depth
            if depth >= max_depth:
                dirs.clear()
                continue
                
            # Skip massive asset/library folders
            for d in list(dirs):
                if d.lower() in ("node_modules", "common files", "microsoft shared", "steamapps", "resources", "temp", "cache"):
                    dirs.remove(d)

            for file in files:
                if file.lower().endswith(".exe"):
                    path = os.path.join(root, file)
                    # Use filename (without extension) as a candidate app name
                    name = Path(file).stem
                    # Do not overwrite start menu or registry mappings which are cleaner
                    if name.lower() not in apps:
                        apps[name.lower()] = AppEntry(
                            name=name,
                            path=path,
                            target_path=path,
                            source="program_files"
                        )

    def _scan_path_executables(self, apps: Dict[str, AppEntry]):
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        for d in path_dirs:
            if not d or not os.path.isdir(d):
                continue
            try:
                for file in os.listdir(d):
                    if file.lower().endswith((".exe", ".cmd", ".bat")):
                        path = os.path.join(d, file)
                        name = Path(file).stem
                        if name.lower() not in apps:
                            apps[name.lower()] = AppEntry(
                                name=name,
                                path=path,
                                target_path=path,
                                source="path"
                            )
            except Exception:
                continue

class MacAppDiscovery(BaseAppDiscovery):
    def discover_apps(self) -> List[AppEntry]:
        apps = {}
        paths = ["/Applications", os.path.expanduser("~/Applications")]
        for p in paths:
            if not os.path.isdir(p):
                continue
            try:
                for item in os.listdir(p):
                    if item.endswith(".app"):
                        full_path = os.path.join(p, item)
                        name = item[:-4]
                        apps[name.lower()] = AppEntry(
                            name=name,
                            path=full_path,
                            target_path=full_path,
                            source="applications"
                        )
            except Exception:
                continue
        return list(apps.values())

class LinuxAppDiscovery(BaseAppDiscovery):
    def discover_apps(self) -> List[AppEntry]:
        apps = {}
        paths = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
        for p in paths:
            if not os.path.isdir(p):
                continue
            try:
                for item in os.listdir(p):
                    if item.endswith(".desktop"):
                        full_path = os.path.join(p, item)
                        self._parse_desktop_file(full_path, apps)
            except Exception:
                continue
        return list(apps.values())

    def _parse_desktop_file(self, path: str, apps: dict):
        try:
            name, exec_path = None, None
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("Name="):
                        name = line.split("=", 1)[1].strip()
                    elif line.startswith("Exec="):
                        # Exec string can contain parameters like %U, %F - clean them
                        exec_raw = line.split("=", 1)[1].strip()
                        exec_path = exec_raw.split(" ")[0].strip('"')
                    if name and exec_path:
                        break
            if name and exec_path:
                apps[name.lower()] = AppEntry(
                    name=name,
                    path=exec_path,
                    target_path=exec_path,
                    source="desktop_file"
                )
        except Exception:
            pass

class AppCacheManager:
    def __init__(self):
        # Place cache in the Backend root directory
        self.cache_file = Path(__file__).resolve().parent.parent / "app_cache.json"

    def get_discovery_engine(self) -> BaseAppDiscovery:
        if sys.platform == "win32":
            return WindowsAppDiscovery()
        elif sys.platform == "darwin":
            return MacAppDiscovery()
        else:
            return LinuxAppDiscovery()

    def load_cache(self) -> List[AppEntry]:
        if not self.cache_file.exists():
            return []
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [AppEntry.from_dict(d) for d in data]
        except Exception as e:
            print(f"DEBUG_LOG: [AppCacheManager] Failed to load cache: {e}")
            return []

    def save_cache(self, apps: List[AppEntry]):
        try:
            data = [app.to_dict() for app in apps]
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"DEBUG_LOG: [AppCacheManager] Cache updated successfully with {len(apps)} apps.")
        except Exception as e:
            print(f"DEBUG_LOG: [AppCacheManager] Failed to save cache: {e}")

    def refresh(self) -> List[AppEntry]:
        print("DEBUG_LOG: [AppCacheManager] Initiating system app discovery scan...")
        engine = self.get_discovery_engine()
        apps = engine.discover_apps()
        self.save_cache(apps)
        return apps

    def load_or_refresh(self) -> List[AppEntry]:
        apps = self.load_cache()
        if not apps:
            apps = self.refresh()
        return apps

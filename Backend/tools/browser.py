import os
import sys
import time
import webbrowser
import httpx
import shutil
import subprocess
import traceback
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pyautogui
import pyperclip
from tools.registry import registry

# Configure PyAutoGUI safety settings
pyautogui.FAILSAFE = True

def check_browser_installed(**kwargs) -> str:
    """Verifies that at least one supported browser is available on the system."""
    if sys.platform == "darwin":
        if os.path.exists("/Applications/Safari.app") or os.path.exists("/Applications/Google Chrome.app"):
            return ""
            
    browsers = ["chrome", "msedge", "firefox", "safari", "google-chrome", "microsoft-edge"]
    if sys.platform == "win32":
        browsers.extend(["chrome.exe", "msedge.exe", "firefox.exe"])
        
    for b in browsers:
        if shutil.which(b):
            return ""
            
    try:
        # Check standard library webbrowser registration
        webbrowser.get()
        return ""
    except Exception:
        return "Prerequisite Failed: No supported web browser detected on the host system."

def get_active_browser_url() -> str:
    """Attempts to retrieve the active browser tab's URL cross-platform with timeouts."""
    if sys.platform == "darwin":
        import subprocess
        script = '''
        tell application "System Events"
            set activeApp to name of first application process whose frontmost is true
            if activeApp is "Safari" then
                tell application "Safari" to return URL of current tab of front window
            else if activeApp is "Google Chrome" then
                tell application "Google Chrome" to return URL of active tab of first window
            end if
        end tell
        return ""
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2.0)
            url = res.stdout.strip()
            if url:
                return url
        except Exception:
            pass

    # Fallback to copy address bar
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        old_clipboard = ""
        
    cmd_key = "command" if sys.platform == "darwin" else "ctrl"
    
    # Safely invoke GUI keys with small delays
    pyautogui.hotkey(cmd_key, "l")
    time.sleep(0.1)
    pyautogui.hotkey(cmd_key, "c")
    time.sleep(0.2)
    
    try:
        copied_url = pyperclip.paste().strip()
        # Restore old clipboard
        pyperclip.copy(old_clipboard)
    except Exception:
        copied_url = ""
        
    if copied_url.startswith(("http://", "https://", "www.")):
        if copied_url.startswith("www."):
            copied_url = "https://" + copied_url
        return copied_url
        
    return ""

def _launch_browser_url(url: str) -> None:
    """
    Launches a URL in the default browser on the current platform.
    Logs parameters, executed command, and exit code / exceptions.
    Throws Exception if launch fails.
    """
    platform = sys.platform
    print(f"DEBUG_LOG: [Browser] Requested URL: '{url}'")
    print(f"DEBUG_LOG: [Browser] Platform: '{platform}'")
    
    if platform == "win32":
        cmd_str = f"os.startfile({url!r})"
        print(f"DEBUG_LOG: [Browser] Browser command executed: {cmd_str}")
        try:
            ret = os.startfile(url)
            print(f"DEBUG_LOG: [Browser] Exit code / return value: {ret}")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"DEBUG_LOG: [Browser] Exception traceback:\n{tb}")
            
            # Fallback to subprocess with "start"
            print("DEBUG_LOG: [Browser] Attempting fallback with subprocess 'start'")
            fallback_cmd = f"start {url}"
            print(f"DEBUG_LOG: [Browser] Browser command executed: {fallback_cmd}")
            try:
                res = subprocess.run(fallback_cmd, shell=True, check=True, capture_output=True, text=True)
                print(f"DEBUG_LOG: [Browser] Exit code / return value: {res.returncode}")
            except Exception as fe:
                tb_fallback = traceback.format_exc()
                print(f"DEBUG_LOG: [Browser] Fallback Exception traceback:\n{tb_fallback}")
                raise RuntimeError(f"Both os.startfile and start command failed to open browser. Error: {str(fe)}") from fe
    elif platform == "darwin":
        cmd = ["open", url]
        print(f"DEBUG_LOG: [Browser] Browser command executed: {cmd}")
        try:
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"DEBUG_LOG: [Browser] Exit code / return value: {res.returncode}")
        except subprocess.CalledProcessError as e:
            tb = traceback.format_exc()
            print(f"DEBUG_LOG: [Browser] Exit code / return value: {e.returncode}")
            print(f"DEBUG_LOG: [Browser] Exception traceback:\n{tb}")
            raise RuntimeError(f"macOS 'open' command failed with exit code {e.returncode}: {e.stderr}") from e
    else:
        cmd = ["xdg-open", url]
        print(f"DEBUG_LOG: [Browser] Browser command executed: {cmd}")
        try:
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"DEBUG_LOG: [Browser] Exit code / return value: {res.returncode}")
        except subprocess.CalledProcessError as e:
            tb = traceback.format_exc()
            print(f"DEBUG_LOG: [Browser] Exit code / return value: {e.returncode}")
            print(f"DEBUG_LOG: [Browser] Exception traceback:\n{tb}")
            raise RuntimeError(f"Linux 'xdg-open' command failed with exit code {e.returncode}: {e.stderr}") from e


@registry.register(
    name="browser_open_url",
    description="Opens one or multiple URLs in the default web browser.",
    parameters={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of URLs to open"
            }
        },
        "required": ["urls"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def browser_open_url(urls: list) -> str:
    results = []
    errors = []
    for url in urls:
        clean_url = url.strip()
        if not clean_url:
            errors.append("Empty URL provided")
            continue

        # Only prepend https:// if the URL has no scheme at all
        parsed = urlparse(clean_url)
        if not parsed.scheme:
            clean_url = "https://" + clean_url
            parsed = urlparse(clean_url)

        # Validate that the URL has a scheme and a network location (hostname)
        if not parsed.scheme or not parsed.netloc:
            err_msg = f"Invalid URL '{clean_url}': missing scheme or hostname"
            print(f"DEBUG_LOG: [Browser] {err_msg}")
            errors.append(err_msg)
            continue

        # Only allow http/https schemes for browser tool
        if parsed.scheme not in ("http", "https"):
            err_msg = f"Unsupported URL scheme '{parsed.scheme}' in '{clean_url}': only http and https are allowed"
            print(f"DEBUG_LOG: [Browser] {err_msg}")
            errors.append(err_msg)
            continue

        try:
            _launch_browser_url(clean_url)
            results.append(clean_url)
        except Exception as e:
            err_msg = f"Failed to open '{clean_url}': {str(e)}"
            errors.append(err_msg)
            
    if errors:
        raise RuntimeError(f"Browser launch failed: {'; '.join(errors)}")
    return f"Opened browser tabs for: {', '.join(results)}"

browser_open_url.check_prerequisites = check_browser_installed


@registry.register(
    name="browser_search",
    description="Performs a search query on Google or YouTube in the default browser.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search term"},
            "engine": {
                "type": "string",
                "enum": ["google", "youtube"],
                "description": "Search engine to use (default: google)"
            }
        },
        "required": ["query"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def browser_search(query: str, engine: str = "google") -> str:
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    
    if engine.lower() == "youtube":
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
    else:
        url = f"https://www.google.com/search?q={encoded_query}"
        
    try:
        _launch_browser_url(url)
    except Exception as e:
        return f"Error searching {engine} for '{query}': {str(e)}"
    return f"Searched {engine} for: '{query}'"

browser_search.check_prerequisites = check_browser_installed


@registry.register(
    name="browser_control",
    description="Sends standard control shortcuts or scrolling events to the active web browser.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "close_tab", "refresh", "back", "forward", 
                    "scroll_up", "scroll_down", "scroll_top", "scroll_bottom"
                ],
                "description": "Browser shortcut or scroll action to trigger"
            },
            "count": {
                "type": "integer",
                "default": 1,
                "description": "Number of times to perform the action"
            }
        },
        "required": ["action"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def browser_control(action: str, count: int = 1) -> str:
    is_mac = sys.platform == "darwin"
    cmd_key = "command" if is_mac else "ctrl"
    
    for _ in range(count):
        if action == "close_tab":
            pyautogui.hotkey(cmd_key, "w")
        elif action == "refresh":
            pyautogui.hotkey(cmd_key, "r")
        elif action == "back":
            if is_mac:
                pyautogui.hotkey("command", "[")
            else:
                pyautogui.hotkey("alt", "left")
        elif action == "forward":
            if is_mac:
                pyautogui.hotkey("command", "]")
            else:
                pyautogui.hotkey("alt", "right")
        elif action == "scroll_up":
            pyautogui.scroll(250)
        elif action == "scroll_down":
            pyautogui.scroll(-250)
        elif action == "scroll_top":
            pyautogui.press("home")
        elif action == "scroll_bottom":
            pyautogui.press("end")
        time.sleep(0.1)
        
    return f"Browser control '{action}' completed successfully {count} times."

browser_control.check_prerequisites = check_browser_installed


@registry.register(
    name="browser_read_page",
    description="Extracts the main readable text content of a webpage. If url is omitted, attempts to read the active browser tab.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Optional URL to fetch"},
            "timeout": {"type": "number", "default": 8.0, "description": "Page load timeout in seconds"}
        }
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def browser_read_page(url: str = None, timeout: float = 8.0) -> str:
    target_url = url
    if not target_url:
        target_url = get_active_browser_url()
        if not target_url:
            return "Error: Could not retrieve active tab URL. Ensure a browser is open and the window is active."
            
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Enforce page load timeout strictly
        with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
            response = client.get(target_url)
            
        if response.status_code != 200:
            return f"Error: Failed to fetch page. HTTP status code {response.status_code}."
            
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()
            
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)
        
        # 1. Content Validation Check
        if not cleaned_text.strip() or len(cleaned_text) < 50:
            return "Error: The extracted page content is empty, or access is blocked by security (Cloudflare/Access Control) rules."
            
        max_chars = 6000
        if len(cleaned_text) > max_chars:
            cleaned_text = cleaned_text[:max_chars] + "\n\n... (Page content truncated for length) ..."
            
        return f"Webpage Title: {soup.title.string if soup.title else 'No Title'}\nWebpage URL: {target_url}\n\nContent:\n{cleaned_text}"
        
    except httpx.TimeoutException:
        return f"Error: Page load timed out after {timeout}s."
    except Exception as e:
        return f"Error reading page content: {str(e)}"

browser_read_page.check_prerequisites = check_browser_installed


@registry.register(
    name="browser_click_link",
    description="Attempts to click a visible link or button containing the specified text using browser search functionality.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "The text of the link or button to click"}
        },
        "required": ["text"]
    },
    safety_level="safe",
    supported_platforms=["windows", "macos", "linux"]
)
def browser_click_link(text: str) -> str:
    cmd_key = "command" if sys.platform == "darwin" else "ctrl"
    
    pyautogui.hotkey(cmd_key, "f")
    time.sleep(0.1)
    pyautogui.write(text, interval=0.01)
    time.sleep(0.2)
    pyautogui.press("escape")
    time.sleep(0.1)
    pyautogui.press("enter")
    
    return f"Executed search-and-click sequence for: '{text}'"

browser_click_link.check_prerequisites = check_browser_installed

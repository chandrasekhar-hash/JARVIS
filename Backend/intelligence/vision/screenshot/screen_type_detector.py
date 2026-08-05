"""
JARVIS Vision Intelligence V5 — Screen Type Detector.

ScreenTypeDetector owns all screenshot specialization.
Given a user prompt, it resolves:
  - ScreenCategory: high-level category (IDE, TERMINAL, BROWSER, etc.)
  - ApplicationHint: specific tool or application detected (optional)

This keeps VisualTask stable and reasoning-type-focused.
VisualTask.SCREENSHOT is the single entry point; this module drives the depth.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List


# ---------------------------------------------------------------------------
# ScreenCategory — High-level categories owned by ScreenTypeDetector
# ---------------------------------------------------------------------------

class ScreenCategory(str, Enum):
    IDE             = "IDE"            # Code editors: VS Code, Cursor, PyCharm, IntelliJ, Android Studio
    TERMINAL        = "TERMINAL"       # bash, zsh, PowerShell, CMD, fish, Git Bash + CLI output
    BROWSER         = "BROWSER"        # Chrome, Firefox, Edge, Safari — web page content
    DEVTOOLS        = "DEVTOOLS"       # Browser Developer Tools tabs (Console, Network, Elements…)
    DASHBOARD       = "DASHBOARD"      # Analytics dashboards, admin panels, KPI cards
    SETTINGS        = "SETTINGS"       # OS or app settings: Windows, macOS, Android, iOS
    MOBILE          = "MOBILE"         # Android or iPhone app/OS screenshots (non-settings)
    DESIGN_TOOL     = "DESIGN_TOOL"    # Figma, Canva, Adobe XD
    DATABASE_TOOL   = "DATABASE_TOOL"  # Supabase, Firebase Console, Postgres UI, Adminer
    DEVELOPER_TOOL  = "DEVELOPER_TOOL" # GitHub, GitLab, Docker, npm/yarn/pnpm, git CLI output
    WEB_APP         = "WEB_APP"        # React, Next.js, FastAPI /docs, Vite app, Notion, Slack
    GENERAL         = "GENERAL"        # Fallback — recognized as screenshot but category unclear


# ---------------------------------------------------------------------------
# ApplicationHint — Optional specific tool recognized within a category
# ---------------------------------------------------------------------------

class ApplicationHint(str, Enum):
    # IDEs
    VSCODE          = "vscode"
    CURSOR          = "cursor"
    PYCHARM         = "pycharm"
    INTELLIJ        = "intellij"
    ANDROID_STUDIO  = "android_studio"
    # Browsers
    CHROME          = "chrome"
    FIREFOX         = "firefox"
    EDGE            = "edge"
    SAFARI          = "safari"
    # Developer Tools
    GITHUB          = "github"
    GITLAB          = "gitlab"
    DOCKER          = "docker"
    NPM             = "npm"
    GIT             = "git"
    FIREBASE        = "firebase"
    SUPABASE        = "supabase"
    # Design Tools
    FIGMA           = "figma"
    CANVA           = "canva"
    # Mobile OS
    ANDROID         = "android"
    IOS             = "ios"
    # Web Frameworks / Apps
    REACT           = "react"
    FASTAPI         = "fastapi"
    NEXTJS          = "nextjs"
    NOTION          = "notion"
    SLACK           = "slack"
    DISCORD         = "discord"
    # Shells / Terminals
    POWERSHELL      = "powershell"
    BASH            = "bash"
    ZSH             = "zsh"
    CMD             = "cmd"
    # Catch-all
    UNKNOWN         = "unknown"


# ---------------------------------------------------------------------------
# ScreenContext — Rich detection result returned by ScreenTypeDetector
# ---------------------------------------------------------------------------

@dataclass
class ScreenContext:
    category: ScreenCategory = ScreenCategory.GENERAL
    app_hint: ApplicationHint = ApplicationHint.UNKNOWN
    # Detected content signals (for template selection and logging)
    has_error: bool = False
    has_code: bool = False
    has_terminal_output: bool = False
    has_ui_controls: bool = False
    has_multi_panel: bool = False
    # Human-readable summary for logging
    description: str = ""


# ---------------------------------------------------------------------------
# Detection rule tables
# ---------------------------------------------------------------------------

# Application-specific patterns: maps regex -> (ScreenCategory, ApplicationHint)
_APP_RULES: List[tuple] = [
    # --- IDEs ---
    (re.compile(r"\b(vscode|vs code|visual studio code)\b", re.I), ScreenCategory.IDE, ApplicationHint.VSCODE),
    (re.compile(r"\bcursor\s*(editor|ide|app)?\b", re.I),          ScreenCategory.IDE, ApplicationHint.CURSOR),
    (re.compile(r"\bpycharm\b", re.I),                              ScreenCategory.IDE, ApplicationHint.PYCHARM),
    (re.compile(r"\b(intellij|idea)\b", re.I),                     ScreenCategory.IDE, ApplicationHint.INTELLIJ),
    (re.compile(r"\bandroid studio\b", re.I),                      ScreenCategory.IDE, ApplicationHint.ANDROID_STUDIO),
    # --- Browsers ---
    (re.compile(r"\bchrome\b(?! devtools| dev tools)", re.I),      ScreenCategory.BROWSER, ApplicationHint.CHROME),
    (re.compile(r"\bfirefox\b", re.I),                             ScreenCategory.BROWSER, ApplicationHint.FIREFOX),
    (re.compile(r"\bedge\s*(browser)?\b", re.I),                   ScreenCategory.BROWSER, ApplicationHint.EDGE),
    (re.compile(r"\bsafari\b", re.I),                              ScreenCategory.BROWSER, ApplicationHint.SAFARI),
    # --- DevTools ---
    (re.compile(r"\b(devtools|dev tools|developer tools|chrome devtools)\b", re.I), ScreenCategory.DEVTOOLS, ApplicationHint.CHROME),
    (re.compile(r"\b(console tab|network tab|elements tab|sources tab|application tab|performance tab|lighthouse)\b", re.I), ScreenCategory.DEVTOOLS, ApplicationHint.CHROME),
    # --- Developer Tools ---
    (re.compile(r"\b(github|gh pr|pull request|code review)\b", re.I),    ScreenCategory.DEVELOPER_TOOL, ApplicationHint.GITHUB),
    (re.compile(r"\bgitlab\b", re.I),                                      ScreenCategory.DEVELOPER_TOOL, ApplicationHint.GITLAB),
    (re.compile(r"\b(docker|docker compose|docker desktop|container)\b", re.I), ScreenCategory.DEVELOPER_TOOL, ApplicationHint.DOCKER),
    (re.compile(r"\b(npm|npx|yarn|pnpm)\b", re.I),                        ScreenCategory.DEVELOPER_TOOL, ApplicationHint.NPM),
    (re.compile(r"\bgit\s+(log|diff|status|commit|push|pull|merge|rebase|clone)\b", re.I), ScreenCategory.DEVELOPER_TOOL, ApplicationHint.GIT),
    # --- Database Tools ---
    (re.compile(r"\bfirebase\s*(console)?\b", re.I),   ScreenCategory.DATABASE_TOOL, ApplicationHint.FIREBASE),
    (re.compile(r"\bsupabase\b", re.I),                ScreenCategory.DATABASE_TOOL, ApplicationHint.SUPABASE),
    # --- Design Tools ---
    (re.compile(r"\bfigma\b", re.I),  ScreenCategory.DESIGN_TOOL, ApplicationHint.FIGMA),
    (re.compile(r"\bcanva\b", re.I),  ScreenCategory.DESIGN_TOOL, ApplicationHint.CANVA),
    # --- Mobile OS ---
    (re.compile(r"\b(android settings|android screen|pixel|samsung phone)\b", re.I), ScreenCategory.MOBILE, ApplicationHint.ANDROID),
    (re.compile(r"\b(iphone|ios|ipad)\b", re.I),                                     ScreenCategory.MOBILE, ApplicationHint.IOS),
    # --- Web Apps ---
    (re.compile(r"\b(react app|react component|react page)\b", re.I),    ScreenCategory.WEB_APP, ApplicationHint.REACT),
    (re.compile(r"\b(fastapi|/docs|swagger ui|openapi)\b", re.I),        ScreenCategory.WEB_APP, ApplicationHint.FASTAPI),
    (re.compile(r"\bnext\.?js\b", re.I),                                  ScreenCategory.WEB_APP, ApplicationHint.NEXTJS),
    (re.compile(r"\bnotion\b", re.I),                                     ScreenCategory.WEB_APP, ApplicationHint.NOTION),
    (re.compile(r"\bslack\b", re.I),                                      ScreenCategory.WEB_APP, ApplicationHint.SLACK),
    (re.compile(r"\bdiscord\b", re.I),                                    ScreenCategory.WEB_APP, ApplicationHint.DISCORD),
]

# Category-level patterns: applied when no app-level rule fires
_CATEGORY_RULES: List[tuple] = [
    (re.compile(r"\b(ide|editor|code editor|debugger|breakpoint|file tree|problems panel)\b", re.I), ScreenCategory.IDE),
    (re.compile(r"\b(terminal|shell|command line|bash|zsh|fish|powershell|cmd|console output|cli output)\b", re.I), ScreenCategory.TERMINAL),
    (re.compile(r"\b(devtools|dev tools|network tab|console tab|elements tab)\b", re.I), ScreenCategory.DEVTOOLS),
    (re.compile(r"\b(browser|webpage|web page|404|503|502|403)\b", re.I), ScreenCategory.BROWSER),
    (re.compile(r"\b(dashboard|admin panel|analytics|kpi|metric card|widget)\b", re.I), ScreenCategory.DASHBOARD),
    (re.compile(r"\b(settings|preferences|system settings|control panel|toggle|enable disable)\b", re.I), ScreenCategory.SETTINGS),
    (re.compile(r"\b(mobile|phone|iphone|android|ios)\b", re.I), ScreenCategory.MOBILE),
    (re.compile(r"\b(figma|design tool|canva|prototype|wireframe|mockup)\b", re.I), ScreenCategory.DESIGN_TOOL),
    (re.compile(r"\b(database|supabase|firebase|table|rows|columns|schema)\b", re.I), ScreenCategory.DATABASE_TOOL),
    (re.compile(r"\b(github|docker|npm|git log|ci\/cd|pipeline)\b", re.I), ScreenCategory.DEVELOPER_TOOL),
]

# Content signal patterns — for ScreenContext flags
_ERROR_SIGNAL = re.compile(r"\b(error|traceback|exception|failed|failure|404|500|cors|crash|red underline|warning)\b", re.I)
_CODE_SIGNAL = re.compile(r"\b(code|function|class|import|variable|syntax|line \d+|highlight)\b", re.I)
_TERMINAL_SIGNAL = re.compile(r"\b(command|output|exit code|stack trace|pip|npm|python|uvicorn|webpack)\b", re.I)
_UI_SIGNAL = re.compile(r"\b(button|form|input|dropdown|dialog|modal|sidebar|navbar|tab)\b", re.I)
_MULTI_PANEL_SIGNAL = re.compile(r"\b(panel|split|and the|both|together|alongside|vs code and|terminal and|browser and)\b", re.I)


class ScreenTypeDetector:
    """
    Owns all screenshot specialization for V5.
    Maps a user prompt to a rich ScreenContext (category + app + content signals).
    Used only for instruction template selection — never for routing.
    """

    def detect(self, prompt: Optional[str] = None) -> ScreenContext:
        """
        Returns a ScreenContext for the given prompt.
        Falls back to GENERAL if no specific signals are found.
        """
        text = (prompt or "").strip()

        category = ScreenCategory.GENERAL
        app_hint = ApplicationHint.UNKNOWN

        # Step 1: Try app-specific rules first (most specific)
        for pattern, cat, app in _APP_RULES:
            if pattern.search(text):
                category = cat
                app_hint = app
                break

        # Step 2: If no app match, try category-level rules
        if category == ScreenCategory.GENERAL:
            for pattern, cat in _CATEGORY_RULES:
                if pattern.search(text):
                    category = cat
                    break

        # Step 3: Detect content signals for template context
        has_error = bool(_ERROR_SIGNAL.search(text))
        has_code = bool(_CODE_SIGNAL.search(text))
        has_terminal_output = bool(_TERMINAL_SIGNAL.search(text))
        has_ui_controls = bool(_UI_SIGNAL.search(text))
        has_multi_panel = bool(_MULTI_PANEL_SIGNAL.search(text))

        description = f"{category.value}"
        if app_hint != ApplicationHint.UNKNOWN:
            description += f" / {app_hint.value}"
        if has_error:
            description += " [error detected]"
        if has_multi_panel:
            description += " [multi-panel]"

        return ScreenContext(
            category=category,
            app_hint=app_hint,
            has_error=has_error,
            has_code=has_code,
            has_terminal_output=has_terminal_output,
            has_ui_controls=has_ui_controls,
            has_multi_panel=has_multi_panel,
            description=description,
        )


# Singleton
screen_type_detector = ScreenTypeDetector()

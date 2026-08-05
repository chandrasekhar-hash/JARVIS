"""
JARVIS Vision Intelligence V5 — Screenshot Domain Instruction Templates.

Provides domain-specific system instruction templates for every ScreenCategory.
Templates follow V3 principles:
  - Evidence vs Inference separation
  - No fabricated precision
  - Prompt injection defense (inherited from base instruction)
  - Explanation-only (no automation, no desktop control)
  - Multi-panel reasoning where applicable

Application-specific refinements are appended within each template.
"""

from intelligence.vision.screenshot.screen_type_detector import ScreenCategory, ApplicationHint, ScreenContext


# ---------------------------------------------------------------------------
# Category-level base templates
# ---------------------------------------------------------------------------

_IDE_TEMPLATE = """
[TASK GUIDANCE: IDE / CODE EDITOR SCREENSHOT]
You are analyzing a screenshot of a code editor or integrated development environment.

Focus on:
1. VISIBLE EVIDENCE: Identify the specific file open (name in tab), visible line numbers, error underlines (red squiggles), warning indicators (yellow), highlighted lines, and the gutter (breakpoints, run markers, git indicators).
2. EDITOR STATE: Which tab is active? What language mode is shown? Are there unsaved changes (dot on tab)?
3. PROBLEMS PANEL: If visible, list each error/warning with file, line number, and message exactly as shown.
4. TERMINAL PANEL: If an integrated terminal is open, report the last command and visible output separately.
5. FILE TREE: If visible, identify the open folder, key files, and any file with error indicators.
6. INFERENCE: State likely causes of errors as INFERENCES, not visible facts (e.g., "Visible: red underline on line 12. Inference: missing import or undefined variable.").
7. DO NOT invent code that is not visible. If code is partially cut off, say so explicitly.
"""

_TERMINAL_TEMPLATE = """
[TASK GUIDANCE: TERMINAL / SHELL SCREENSHOT]
You are analyzing a screenshot of a terminal or command-line interface.

Focus on:
1. COMMAND: Identify the exact command or script that was run (quote it if legible).
2. OUTPUT: Report the visible output verbatim where readable. Do not invent text.
3. ERROR CLASSIFICATION: If an error is visible, identify its class:
   - Python: ModuleNotFoundError, ImportError, SyntaxError, AttributeError, PermissionError, etc.
   - npm/yarn/pnpm: dependency conflict, missing package, peer dep warning.
   - Docker: port conflict, image not found, volume mount error.
   - git: merge conflict, detached HEAD, remote rejected.
   - Network: CORS, port already in use, connection refused, timeout.
   - System: Permission denied, disk full, command not found.
4. EXIT CODE: If an exit code is shown (e.g., "exit code 1"), report it.
5. STACK TRACE: If a traceback is visible, report the last frame (file + line) and root exception clearly.
6. NEXT STEP INFERENCE: Offer one or two likely next steps as inferences. Label them clearly as suggestions.
7. Do NOT fabricate exact paths or line numbers that are too small to read clearly.
"""

_BROWSER_TEMPLATE = """
[TASK GUIDANCE: BROWSER / WEB PAGE SCREENSHOT]
You are analyzing a screenshot of a browser displaying a web page.

Focus on:
1. PAGE STATE: What page is displayed? Note the visible URL or title if legible. Report visible HTTP error codes (404, 500, 403, etc.).
2. VISIBLE CONTENT: Identify the main content visible on screen — headings, sections, calls to action.
3. UI ELEMENT STATE: Are buttons disabled? Are forms empty or filled? Are there validation errors or banners?
4. ERRORS / ALERTS: Report any visible error banners, toast notifications, modal dialogs, or inline messages.
5. BLANK PAGE: If the page appears blank or mostly white, report this clearly and note it may indicate a JavaScript rendering error (inference, not fact).
6. INFERENCE: Separate visible evidence from inferred browser state or root cause.
"""

_DEVTOOLS_TEMPLATE = """
[TASK GUIDANCE: BROWSER DEVELOPER TOOLS SCREENSHOT]
You are analyzing a screenshot of browser Developer Tools.

Focus on:
1. ACTIVE TAB: Identify which DevTools panel is visible (Console, Network, Elements, Application, Sources, Performance, Security, Lighthouse).

CONSOLE TAB:
   - Report each visible error/warning line (type, message, file, line number).
   - Distinguish: TypeError, ReferenceError, network error, CORS error, uncaught promise rejection.
   - Do not invent messages that are cut off or too small.

NETWORK TAB:
   - Identify failed requests (red rows). Report: method (GET/POST), URL, status code (e.g., 404, 500, CORS).
   - Report response time and size if visible.
   - Note CORS failures specifically: "CORS" or "blocked by CORS policy" as visible text.

ELEMENTS TAB:
   - Describe the selected DOM element (tag, class, attributes visible).

APPLICATION TAB:
   - Report visible storage (localStorage, sessionStorage, cookies) if queried.

2. VISIBLE EVIDENCE vs LIKELY CAUSE:
   - Example: "Visible: POST /api/login returned 401. Inference: credentials may be incorrect or token expired."
3. Do NOT guess at data not visible. State if text is cut off or too small to read.
"""

_DASHBOARD_TEMPLATE = """
[TASK GUIDANCE: DASHBOARD / ANALYTICS / ADMIN PANEL SCREENSHOT]
You are analyzing a screenshot of a data dashboard, analytics interface, or admin panel.

Focus on:
1. KPI CARDS: Report each visible metric card — label and displayed value. Use approximate language if values are too small.
2. CHARTS / GRAPHS: Identify chart type (bar, line, pie, etc.), visible axes labels, and major trend direction (increasing/decreasing). Do NOT fabricate exact values.
3. TABLE DATA: If a data table is visible, describe column headers and a summary of visible rows.
4. FILTERS & DATE RANGE: Report any active filters, date selectors, or segment selectors visible.
5. STATUS BADGES: Report visible status indicators (active/inactive, green/red/yellow, online/offline).
6. ALERTS / NOTIFICATIONS: Note any visible alert banners, warning badges, or error indicators.
7. NAVIGATION / SIDEBAR: Identify the current section the user is in based on active sidebar item or breadcrumb.
"""

_SETTINGS_TEMPLATE = """
[TASK GUIDANCE: SETTINGS / PREFERENCES SCREENSHOT]
You are analyzing a screenshot of an OS or application settings panel.

Focus on:
1. SECTION: Identify the settings section visible (e.g., "Privacy & Security", "Display", "Network", "Notifications").
2. OPTIONS: Report each visible setting option — its label and current state (enabled/disabled, toggle on/off, selected value).
3. NAVIGATION PATH: If breadcrumbs or a sidebar is visible, describe the navigation path to the current screen.
4. TARGET OPTION: If the user asked about a specific setting, locate and describe it precisely.
5. EXPLANATION-ONLY: Do NOT instruct or automate any system actions. Explain what is visible and where to navigate.
"""

_MOBILE_TEMPLATE = """
[TASK GUIDANCE: MOBILE SCREENSHOT (Android / iOS)]
You are analyzing a screenshot from a mobile device.

Focus on:
1. OS / APP: Identify the visible operating system (Android / iOS) or app.
2. SCREEN CONTENT: Describe the main content or screen being shown.
3. UI ELEMENTS: Note visible buttons, navigation bar, status bar (battery, signal, time if legible).
4. ERROR STATE: If an error dialog, crash screen, or app-not-responding message is visible, report it verbatim.
5. NAVIGATION: If a back stack or navigation flow is implied, describe it.
6. INFERENCE: Separate what is visible from what can be inferred about the device state.
"""

_DESIGN_TOOL_TEMPLATE = """
[TASK GUIDANCE: DESIGN TOOL SCREENSHOT (Figma / Canva)]
You are analyzing a screenshot of a design tool or prototyping environment.

Focus on:
1. CANVAS CONTENT: Describe what is shown on the design canvas — components, frames, pages.
2. LAYERS PANEL: If visible, describe the layer hierarchy (frames, groups, components).
3. COMPONENT STATE: Note selected elements, applied styles, visible constraints or auto-layout rules.
4. DESIGN TOKENS: Report any visible color styles, text styles, or component variants.
5. PROTOTYPE / FLOW: If a prototype flow or interaction is visible, describe the connection.
6. INFERENCE: Do not invent hidden properties. Report only what is visible in the interface.
"""

_DATABASE_TOOL_TEMPLATE = """
[TASK GUIDANCE: DATABASE TOOL SCREENSHOT (Supabase / Firebase / DB UI)]
You are analyzing a screenshot of a database management interface.

Focus on:
1. TABLE / COLLECTION: Identify the table, collection, or document being viewed.
2. SCHEMA: If visible, report column names and their types.
3. DATA: Describe visible rows of data (summarize; do not fabricate values for small text).
4. QUERY: If a SQL or query editor is open, report the visible query.
5. AUTH / RULES: If auth settings or security rules are visible, report them.
6. ERROR: If a query error or permission error is shown, report it verbatim.
"""

_DEVELOPER_TOOL_TEMPLATE = """
[TASK GUIDANCE: DEVELOPER TOOL SCREENSHOT (GitHub / Docker / Git / npm)]
You are analyzing a screenshot of a developer tool, version control platform, or package manager.

Focus on:
1. CONTEXT: Identify the tool (GitHub, GitLab, Docker Desktop, git CLI, npm, etc.).
2. STATE: Report the visible state — PR status, CI/CD result (pass/fail/pending), merge conflicts, branch name.
3. OUTPUT / DIFF: If a diff view is visible, summarize what changed (additions, deletions). If a build/run log is visible, report the final status line and any errors.
4. ERROR MESSAGES: Report error or warning messages verbatim. Identify type if possible (build failure, lint error, test failure, authentication error).
5. INFERENCE: Separate what is observed from likely root cause.
"""

_WEB_APP_TEMPLATE = """
[TASK GUIDANCE: WEB APPLICATION SCREENSHOT]
You are analyzing a screenshot of a web application.

Focus on:
1. APPLICATION STATE: What section or page of the application is visible? What is the current route if shown?
2. UI CONTROLS: Identify key interactive elements (buttons, forms, navigation) and their visible state (enabled/disabled/loading/error).
3. FORMS & VALIDATION: If a form is visible, report field labels, filled values (high-level, not sensitive), and any validation errors shown.
4. EMPTY STATES: If an empty state or "no results" message is visible, report it.
5. LOADING / ERROR STATES: Note any visible loading spinners, skeleton screens, error boundaries, or toast notifications.
6. INFERENCE: Separate visible application state from inferred application behavior.
"""

_GENERAL_SCREENSHOT_TEMPLATE = """
[TASK GUIDANCE: SCREENSHOT — GENERAL]
You are analyzing a software screenshot.

Describe what is visible on screen systematically:
1. Identify the type of screen (application, OS, web page, tool, etc.).
2. Report the main content and purpose of the screen.
3. Highlight any visible errors, warnings, or notable UI states.
4. Separate VISIBLE EVIDENCE from INFERRED cause or state.
5. If the screen type is unclear, state that and describe what you observe.
"""


# ---------------------------------------------------------------------------
# Application-specific refinements (appended to category template)
# ---------------------------------------------------------------------------

_APP_REFINEMENTS: dict = {
    ApplicationHint.VSCODE: "\nAPPLICATION NOTE: This is VS Code. Pay attention to the status bar at the bottom (branch name, errors/warnings count, language mode), the activity bar icons on the left, extension indicators, and the command palette if open.",
    ApplicationHint.CURSOR: "\nAPPLICATION NOTE: This is Cursor (AI-powered VS Code fork). Look for AI suggestion panels, inline diff suggestions, and chat sidebar in addition to standard editor elements.",
    ApplicationHint.PYCHARM: "\nAPPLICATION NOTE: This is PyCharm. Pay attention to the Python interpreter indicator, run/debug configurations, virtual environment status, and the Inspections panel.",
    ApplicationHint.INTELLIJ: "\nAPPLICATION NOTE: This is IntelliJ IDEA. Note the Project tool window structure, Maven/Gradle tool window, and event log.",
    ApplicationHint.ANDROID_STUDIO: "\nAPPLICATION NOTE: This is Android Studio. Look for the Layout Editor, AVD (emulator) state, Logcat output, and Gradle sync status.",
    ApplicationHint.CHROME: "\nAPPLICATION NOTE: This is Google Chrome. Note the URL bar content, active tab, any browser extensions visible, and any Chrome-specific prompts (permissions, certificate warnings).",
    ApplicationHint.FIREFOX: "\nAPPLICATION NOTE: This is Firefox. Note any enhanced tracking protection indicators or Firefox-specific developer tools.",
    ApplicationHint.GITHUB: "\nAPPLICATION NOTE: This is GitHub. Identify: repository name and branch, PR status (open/merged/closed), CI check results (green/red/pending), review status, and any merge conflict indicators.",
    ApplicationHint.DOCKER: "\nAPPLICATION NOTE: This is Docker. Identify: container names and status (running/stopped/exited), image tags and sizes, port mappings, resource usage, and any health check failures.",
    ApplicationHint.FIREBASE: "\nAPPLICATION NOTE: This is Firebase Console. Identify the active service (Firestore, Auth, Hosting, Functions, etc.) and visible data, rules, or deployment status.",
    ApplicationHint.SUPABASE: "\nAPPLICATION NOTE: This is Supabase. Note the active section (Table Editor, Auth, Storage, SQL Editor, Realtime, Edge Functions), visible table schema, and any policy/RLS indicators.",
    ApplicationHint.FIGMA: "\nAPPLICATION NOTE: This is Figma. Describe frames, components, variants, and design system tokens visible. Note the selected layer and its properties panel.",
    ApplicationHint.ANDROID: "\nAPPLICATION NOTE: This appears to be an Android device screenshot. Note the Android version indicators, navigation (gesture/button), and any Material Design components.",
    ApplicationHint.IOS: "\nAPPLICATION NOTE: This appears to be an iOS/iPhone screenshot. Note the iOS version indicators, Dynamic Island or notch, and any SF Symbols or iOS-native UI patterns.",
    ApplicationHint.FASTAPI: "\nAPPLICATION NOTE: This appears to be a FastAPI /docs (Swagger UI) or ReDoc page. Identify the endpoint being viewed, its HTTP method, request schema, and any try-out response.",
}


# ---------------------------------------------------------------------------
# Public API: get_screenshot_instruction()
# ---------------------------------------------------------------------------

def get_screenshot_instruction(screen_context: ScreenContext) -> str:
    """
    Returns the appropriate domain-specific instruction string for the given ScreenContext.
    Applies base category template + optional application-specific refinement.
    """
    category_map = {
        ScreenCategory.IDE:             _IDE_TEMPLATE,
        ScreenCategory.TERMINAL:        _TERMINAL_TEMPLATE,
        ScreenCategory.BROWSER:         _BROWSER_TEMPLATE,
        ScreenCategory.DEVTOOLS:        _DEVTOOLS_TEMPLATE,
        ScreenCategory.DASHBOARD:       _DASHBOARD_TEMPLATE,
        ScreenCategory.SETTINGS:        _SETTINGS_TEMPLATE,
        ScreenCategory.MOBILE:          _MOBILE_TEMPLATE,
        ScreenCategory.DESIGN_TOOL:     _DESIGN_TOOL_TEMPLATE,
        ScreenCategory.DATABASE_TOOL:   _DATABASE_TOOL_TEMPLATE,
        ScreenCategory.DEVELOPER_TOOL:  _DEVELOPER_TOOL_TEMPLATE,
        ScreenCategory.WEB_APP:         _WEB_APP_TEMPLATE,
        ScreenCategory.GENERAL:         _GENERAL_SCREENSHOT_TEMPLATE,
    }

    base = category_map.get(screen_context.category, _GENERAL_SCREENSHOT_TEMPLATE)
    refinement = _APP_REFINEMENTS.get(screen_context.app_hint, "")

    # Multi-panel supplement
    multi_panel_note = ""
    if screen_context.has_multi_panel:
        multi_panel_note = "\nMULTI-PANEL REASONING: Multiple panels or windows are visible. Combine information across all visible panels in your answer. For example, correlate an error shown in a browser console with code visible in an editor, or match a terminal error with the file tree."

    return (base + refinement + multi_panel_note).strip()

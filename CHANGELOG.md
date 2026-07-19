# Changelog
All notable changes to the JARVIS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-19
### Added
- **DesktopService Abstraction**: Introduced a platform-independent Rust trait wrapper dividing concrete platform capabilities (e.g., Windows Win32) from host stubs.
- **Unified Command Dispatcher**: Implemented a generic `dispatch_desktop_operation` Tauri command to handle all native operations via structured payload serialization.
- **Tauri Permission Manager**: Integrated a security validation layer mapping operation safety levels (`safe`, `sensitive`, `destructive`) with native OS modal confirmation dialog intercepts.
- **Asymmetric Bridge**: Developed a thread-safe asynchronous request/response queue over FastAPI SSE channels, enabling deep-nested Python tools to schedule desktop tasks.
- **Window Snapping & Layouts**: Added snapping controls (`SnapLeft`, `SnapRight`, `SnapTop`, `SnapBottom`, `Center`) and custom coordinates utilizing the Win32 `SetWindowPos` and `SPI_GETWORKAREA` APIs.
- **Clipboard & Notification Tools**: Exposed system clipboard read/write actions and native toast notification prompts as registered backend agent capabilities.
- **Native OS Dialogs**: Implemented native file and folder selector dialogs running outside the UI thread pool to prevent system lockups.
- **System Tray Menu**: Added a background status widget providing quick toggles (`Show JARVIS`, `Hide JARVIS`, `Exit`) and runtime states.
- **Global Hotkey Toggle**: Registered the `Alt + Space` global shortcut to toggle webview window visibility dynamically.

### Changed
- **Thread Safety**: Eliminated static locks in window callbacks by passing pointers dynamically inside Win32 callback arguments.
- **Bridge Memory Efficiency**: Added dynamic key popping on timeouts and callback resolutions inside `bridge.py` to prevent memory leaks.
- **Dialog Picker Execution**: Cleaned up file/folder picker routines in `windows.rs` by calling blocking selections directly without redundant async task wrappers.

### Fixed
- **Safety Level Enforcements**: Updated Python PermissionManager to correctly recognize `sensitive` and `destructive` operations mapping from Tauri.
- **Test Discovery Unicode Crash**: Configured `PYTHONIOENCODING=utf-8` on test suites to prevent PowerShell CP1252 code page failures when printing Unicode arrow symbols.

---

## [0.1.0] - 2026-07-15
### Added
- **Core AI Assistant Runtime**: Initial stable release featuring local FastAPI backend, speech transcription, text-to-speech audio outputs, and agentic tool routing.
- **React Frontend**: Implemented Terminal chat shell UI, local status indicators, and state tracking.

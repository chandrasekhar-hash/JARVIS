use crate::desktop::service::{DesktopService, WindowInfo, WindowAction, ProcessInfo};
use tauri::AppHandle;

pub struct MockDesktopService {
    _app_handle: AppHandle,
}

impl MockDesktopService {
    pub fn new(app_handle: AppHandle) -> Self {
        MockDesktopService { _app_handle: app_handle }
    }
}

impl DesktopService for MockDesktopService {
    fn list_windows(&self) -> Result<Vec<WindowInfo>, String> {
        Err("Window listing is only supported on Windows".to_string())
    }

    fn control_window(&self, _handle: u32, _action: WindowAction) -> Result<(), String> {
        Err("Window control is only supported on Windows".to_string())
    }

    fn list_processes(&self) -> Result<Vec<ProcessInfo>, String> {
        Err("Process listing is only supported on Windows".to_string())
    }

    fn terminate_process(&self, _pid: u32, _graceful: bool) -> Result<(), String> {
        Err("Process termination is only supported on Windows".to_string())
    }

    fn read_clipboard(&self) -> Result<String, String> {
        Err("Clipboard read is not supported on this platform".to_string())
    }

    fn write_clipboard(&self, _content: String) -> Result<(), String> {
        Err("Clipboard write is not supported on this platform".to_string())
    }

    fn system_notify(&self, _title: String, _body: String) -> Result<(), String> {
        Err("System notifications are not supported on this platform".to_string())
    }

    fn select_file(&self) -> Result<String, String> {
        Err("File picker dialog is not supported on this platform".to_string())
    }

    fn select_folder(&self) -> Result<String, String> {
        Err("Folder picker dialog is not supported on this platform".to_string())
    }
}

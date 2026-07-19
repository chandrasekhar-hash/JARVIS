use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowInfo {
    pub handle: u32,
    pub title: String,
    pub process_id: u32,
    pub process_name: String,
    pub is_minimized: bool,
    pub is_maximized: bool,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
#[serde(tag = "action", content = "params")]
#[serde(rename_all = "lowercase")]
pub enum WindowAction {
    #[default]
    #[serde(rename = "focus")]
    Focus,
    #[serde(rename = "minimize")]
    Minimize,
    #[serde(rename = "maximize")]
    Maximize,
    #[serde(rename = "restore")]
    Restore,
    #[serde(rename = "close")]
    Close,
    #[serde(rename = "snapleft")]
    SnapLeft,
    #[serde(rename = "snapright")]
    SnapRight,
    #[serde(rename = "snaptop")]
    SnapTop,
    #[serde(rename = "snapbottom")]
    SnapBottom,
    #[serde(rename = "center")]
    Center,
    #[serde(rename = "moveresize")]
    MoveResize { x: i32, y: i32, width: i32, height: i32 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessInfo {
    pub pid: u32,
    pub name: String,
    pub memory_mb: u64,
}

pub trait DesktopService {
    fn list_windows(&self) -> Result<Vec<WindowInfo>, String>;
    fn control_window(&self, handle: u32, action: WindowAction) -> Result<(), String>;
    fn list_processes(&self) -> Result<Vec<ProcessInfo>, String>;
    fn terminate_process(&self, pid: u32, graceful: bool) -> Result<(), String>;
    
    // Clipboard Operations
    fn read_clipboard(&self) -> Result<String, String>;
    fn write_clipboard(&self, content: String) -> Result<(), String>;
    
    // Native Notifications
    fn system_notify(&self, title: String, body: String) -> Result<(), String>;
    
    // Native Dialogs
    fn select_file(&self) -> Result<String, String>;
    fn select_folder(&self) -> Result<String, String>;
}

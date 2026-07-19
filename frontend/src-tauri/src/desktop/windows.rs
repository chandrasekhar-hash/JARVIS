use std::mem;
use std::path::Path;
use crate::desktop::service::{DesktopService, WindowInfo, WindowAction, ProcessInfo};
use tauri::AppHandle;
use tauri_plugin_clipboard_manager::ClipboardExt;
use tauri_plugin_notification::NotificationExt;
use tauri_plugin_dialog::DialogExt;

use windows_sys::Win32::Foundation::{
    HWND, LPARAM, BOOL, CloseHandle, FALSE, TRUE, RECT
};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    EnumWindows, IsWindowVisible, GetWindowTextW, GetWindowThreadProcessId,
    ShowWindow, SetForegroundWindow, IsIconic, IsZoomed, PostMessageW,
    WM_CLOSE, SW_MINIMIZE, SW_MAXIMIZE, SW_RESTORE, SW_SHOW,
    SystemParametersInfoW, SPI_GETWORKAREA, SetWindowPos, SWP_NOZORDER, SWP_NOACTIVATE, IsWindow
};
use windows_sys::Win32::System::Threading::{
    OpenProcess, TerminateProcess, PROCESS_QUERY_INFORMATION, PROCESS_TERMINATE, PROCESS_VM_READ,
    QueryFullProcessImageNameW
};
use windows_sys::Win32::System::Diagnostics::ToolHelp::{
    CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W, TH32CS_SNAPPROCESS
};
use windows_sys::Win32::System::ProcessStatus::{
    GetProcessMemoryInfo, PROCESS_MEMORY_COUNTERS
};

pub struct WindowsDesktopService {
    app_handle: AppHandle,
}

impl WindowsDesktopService {
    pub fn new(app_handle: AppHandle) -> Self {
        WindowsDesktopService { app_handle }
    }
}

unsafe extern "system" fn enum_windows_callback(hwnd: HWND, lparam: LPARAM) -> BOOL {
    if IsWindowVisible(hwnd) == 0 {
        return TRUE;
    }

    let mut title_buf = [0u16; 512];
    let title_len = GetWindowTextW(hwnd, title_buf.as_mut_ptr(), title_buf.len() as i32);
    if title_len == 0 {
        return TRUE;
    }
    let title = String::from_utf16_lossy(&title_buf[..title_len as usize]).trim().to_string();
    if title.is_empty() {
        return TRUE;
    }

    let mut process_id = 0u32;
    GetWindowThreadProcessId(hwnd, &mut process_id);

    let process_name = get_process_name_by_pid(process_id);
    let is_minimized = IsIconic(hwnd) != 0;
    let is_maximized = IsZoomed(hwnd) != 0;

    let windows_vec = &mut *(lparam as *mut Vec<WindowInfo>);
    windows_vec.push(WindowInfo {
        handle: hwnd as usize as u32,
        title,
        process_id,
        process_name,
        is_minimized,
        is_maximized,
    });

    TRUE
}

unsafe fn get_process_name_by_pid(pid: u32) -> String {
    let handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if handle == 0 {
        return "Unknown".to_string();
    }

    let mut path_buf = [0u16; 1024];
    let mut size = path_buf.len() as u32;
    let success = QueryFullProcessImageNameW(handle, 0, path_buf.as_mut_ptr(), &mut size);
    CloseHandle(handle);

    if success != 0 {
        let full_path = String::from_utf16_lossy(&path_buf[..size as usize]);
        Path::new(&full_path)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("Unknown")
            .to_string()
    } else {
        "Unknown".to_string()
    }
}

impl DesktopService for WindowsDesktopService {
    fn list_windows(&self) -> Result<Vec<WindowInfo>, String> {
        let mut windows = Vec::new();
        let lparam = &mut windows as *mut Vec<WindowInfo> as LPARAM;

        unsafe {
            if EnumWindows(Some(enum_windows_callback), lparam) == 0 {
                return Err("Failed to enumerate windows".to_string());
            }
        }

        Ok(windows)
    }

    fn control_window(&self, handle: u32, action: WindowAction) -> Result<(), String> {
        let hwnd = handle as usize as HWND;
        
        // 1. Verify window exists and is valid
        unsafe {
            if IsWindow(hwnd) == 0 {
                return Err(format!("Window handle {} is invalid or does not exist", handle));
            }
        }

        unsafe {
            match action {
                WindowAction::Focus => {
                    if IsIconic(hwnd) != 0 {
                        ShowWindow(hwnd, SW_RESTORE);
                    } else {
                        ShowWindow(hwnd, SW_SHOW);
                    }
                    SetForegroundWindow(hwnd);
                }
                WindowAction::Minimize => {
                    ShowWindow(hwnd, SW_MINIMIZE);
                }
                WindowAction::Maximize => {
                    ShowWindow(hwnd, SW_MAXIMIZE);
                }
                WindowAction::Restore => {
                    ShowWindow(hwnd, SW_RESTORE);
                }
                WindowAction::Close => {
                    PostMessageW(hwnd, WM_CLOSE, 0, 0);
                }
                WindowAction::SnapLeft | WindowAction::SnapRight | WindowAction::SnapTop | WindowAction::SnapBottom | WindowAction::Center | WindowAction::MoveResize { .. } => {
                    let mut work_area: RECT = mem::zeroed();
                    if SystemParametersInfoW(SPI_GETWORKAREA, 0, &mut work_area as *mut _ as *mut _, 0) == 0 {
                        return Err("Failed to retrieve screen work area".to_string());
                    }

                    let screen_w = work_area.right - work_area.left;
                    let screen_h = work_area.bottom - work_area.top;

                    let (x, y, w, h) = match action {
                        WindowAction::SnapLeft => {
                            (work_area.left, work_area.top, screen_w / 2, screen_h)
                        }
                        WindowAction::SnapRight => {
                            (work_area.left + screen_w / 2, work_area.top, screen_w / 2, screen_h)
                        }
                        WindowAction::SnapTop => {
                            (work_area.left, work_area.top, screen_w, screen_h / 2)
                        }
                        WindowAction::SnapBottom => {
                            (work_area.left, work_area.top + screen_h / 2, screen_w, screen_h / 2)
                        }
                        WindowAction::Center => {
                            let width = (screen_w * 2) / 3;
                            let height = (screen_h * 2) / 3;
                            let left = work_area.left + (screen_w - width) / 2;
                            let top = work_area.top + (screen_h - height) / 2;
                            (left, top, width, height)
                        }
                        WindowAction::MoveResize { x, y, width, height } => {
                            (x, y, width, height)
                        }
                        _ => unreachable!(),
                    };

                    // Restore window if minimized/maximized to allow correct resize/move
                    if IsIconic(hwnd) != 0 || IsZoomed(hwnd) != 0 {
                        ShowWindow(hwnd, SW_RESTORE);
                    }

                    let success = SetWindowPos(hwnd, 0 as HWND, x, y, w, h, SWP_NOZORDER | SWP_NOACTIVATE);
                    if success == 0 {
                        return Err("Failed to reposition window via SetWindowPos".to_string());
                    }
                }
            }
        }
        Ok(())
    }

    fn list_processes(&self) -> Result<Vec<ProcessInfo>, String> {
        let mut processes = Vec::new();
        unsafe {
            let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
            if snapshot == 0 {
                return Err("Failed to create toolhelp process snapshot".to_string());
            }

            let mut entry: PROCESSENTRY32W = mem::zeroed();
            entry.dwSize = mem::size_of::<PROCESSENTRY32W>() as u32;

            if Process32FirstW(snapshot, &mut entry) != 0 {
                loop {
                    let end_idx = entry.szExeFile.iter().position(|&c| c == 0).unwrap_or(entry.szExeFile.len());
                    let name = String::from_utf16_lossy(&entry.szExeFile[..end_idx]);

                    let pid = entry.th32ProcessID;

                    let mut memory_mb = 0u64;
                    let p_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
                    if p_handle != 0 {
                        let mut counters: PROCESS_MEMORY_COUNTERS = mem::zeroed();
                        counters.cb = mem::size_of::<PROCESS_MEMORY_COUNTERS>() as u32;
                        if GetProcessMemoryInfo(p_handle, &mut counters, counters.cb) != 0 {
                            memory_mb = counters.WorkingSetSize as u64 / (1024 * 1024);
                        }
                        CloseHandle(p_handle);
                    }

                    processes.push(ProcessInfo {
                        pid,
                        name,
                        memory_mb,
                    });

                    if Process32NextW(snapshot, &mut entry) == 0 {
                        break;
                    }
                }
            }
            CloseHandle(snapshot);
        }
        Ok(processes)
    }

    fn terminate_process(&self, pid: u32, graceful: bool) -> Result<(), String> {
        unsafe {
            if graceful {
                let mut windows: Vec<WindowInfo> = Vec::new();
                let lparam = &mut windows as *mut Vec<WindowInfo> as LPARAM;
                let _ = EnumWindows(Some(enum_windows_callback), lparam);
                
                let window_handles: Vec<u32> = windows.iter()
                    .filter(|w| w.process_id == pid)
                    .map(|w| w.handle)
                    .collect();

                if !window_handles.is_empty() {
                    for handle in window_handles {
                        let hwnd = handle as usize as HWND;
                        PostMessageW(hwnd, WM_CLOSE, 0, 0);
                    }
                    std::thread::sleep(std::time::Duration::from_millis(500));
                }
            }

            let p_handle = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
            if p_handle != 0 {
                let success = TerminateProcess(p_handle, 1);
                CloseHandle(p_handle);
                if success == 0 {
                    return Err(format!("TerminateProcess failed for PID {}", pid));
                }
            } else {
                return Err(format!("Failed to open process PID {} with TERMINATE rights", pid));
            }
        }
        Ok(())
    }

    fn read_clipboard(&self) -> Result<String, String> {
        self.app_handle.clipboard().read_text().map_err(|e| e.to_string())
    }

    fn write_clipboard(&self, content: String) -> Result<(), String> {
        self.app_handle.clipboard().write_text(content).map_err(|e| e.to_string())
    }

    fn system_notify(&self, title: String, body: String) -> Result<(), String> {
        self.app_handle.notification().builder()
            .title(&title)
            .body(&body)
            .show()
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    fn select_file(&self) -> Result<String, String> {
        let picked = self.app_handle.dialog().file().blocking_pick_file();
        if let Some(file_path) = picked {
            Ok(file_path.to_string())
        } else {
            Err("Operation Cancelled: No file selected.".to_string())
        }
    }

    fn select_folder(&self) -> Result<String, String> {
        let picked = self.app_handle.dialog().file().blocking_pick_folder();
        if let Some(folder_path) = picked {
            Ok(folder_path.to_string())
        } else {
            Err("Operation Cancelled: No folder selected.".to_string())
        }
    }
}

use std::sync::Arc;
use serde_json::{Value, json};
use tauri::State;
use crate::desktop::service::{DesktopService, WindowAction};
use crate::desktop::permissions::PermissionManager;

#[tauri::command]
pub async fn dispatch_desktop_operation(
    desktop_service: State<'_, Arc<dyn DesktopService + Send + Sync>>,
    perm_manager: State<'_, Arc<PermissionManager>>,
    op: String,
    args: Value,
) -> Result<Value, String> {
    log::info!("[Dispatcher] Dispatching operation: {} with args: {:?}", op, args);

    // Verify permissions via Permission Manager before execution
    perm_manager.verify_permission(&op, &args).await?;

    // Route the action to DesktopService
    match op.as_str() {
        "window:list" => {
            let windows = desktop_service.list_windows()?;
            Ok(json!(windows))
        }
        "window:control" => {
            let handle = args.get("handle")
                .and_then(|h| h.as_u64())
                .ok_or_else(|| "Missing required parameter 'handle'".to_string())? as u32;
            let action_str = args.get("action")
                .and_then(|a| a.as_str())
                .ok_or_else(|| "Missing required parameter 'action'".to_string())?;

            let action = match action_str {
                "focus" => WindowAction::Focus,
                "minimize" => WindowAction::Minimize,
                "maximize" => WindowAction::Maximize,
                "restore" => WindowAction::Restore,
                "close" => WindowAction::Close,
                "snapleft" => WindowAction::SnapLeft,
                "snapright" => WindowAction::SnapRight,
                "snaptop" => WindowAction::SnapTop,
                "snapbottom" => WindowAction::SnapBottom,
                "center" => WindowAction::Center,
                "moveresize" => {
                    let x = args.get("x").and_then(|x| x.as_i64()).ok_or_else(|| "Missing required parameter 'x'".to_string())? as i32;
                    let y = args.get("y").and_then(|y| y.as_i64()).ok_or_else(|| "Missing required parameter 'y'".to_string())? as i32;
                    let w = args.get("width").and_then(|w| w.as_i64()).ok_or_else(|| "Missing required parameter 'width'".to_string())? as i32;
                    let h = args.get("height").and_then(|h| h.as_i64()).ok_or_else(|| "Missing required parameter 'height'".to_string())? as i32;
                    WindowAction::MoveResize { x, y, width: w, height: h }
                }
                _ => return Err(format!("Unsupported window action: {}", action_str)),
            };

            desktop_service.control_window(handle, action)?;
            Ok(json!({"status": "success"}))
        }
        "process:list" => {
            let processes = desktop_service.list_processes()?;
            Ok(json!(processes))
        }
        "process:terminate" => {
            let pid = args.get("pid")
                .and_then(|p| p.as_u64())
                .ok_or_else(|| "Missing required parameter 'pid'".to_string())? as u32;
            let graceful = args.get("graceful")
                .and_then(|g| g.as_bool())
                .unwrap_or(true);

            desktop_service.terminate_process(pid, graceful)?;
            Ok(json!({"status": "success"}))
        }
        "clipboard:read" => {
            let text = desktop_service.read_clipboard()?;
            Ok(json!(text))
        }
        "clipboard:write" => {
            let content = args.get("content")
                .and_then(|c| c.as_str())
                .ok_or_else(|| "Missing required parameter 'content'".to_string())?
                .to_string();
            desktop_service.write_clipboard(content)?;
            Ok(json!({"status": "success"}))
        }
        "system:notify" => {
            let title = args.get("title")
                .and_then(|t| t.as_str())
                .unwrap_or("JARVIS")
                .to_string();
            let body = args.get("body")
                .and_then(|b| b.as_str())
                .ok_or_else(|| "Missing required parameter 'body'".to_string())?
                .to_string();
            desktop_service.system_notify(title, body)?;
            Ok(json!({"status": "success"}))
        }
        "dialog:select_file" => {
            let path = desktop_service.select_file()?;
            Ok(json!(path))
        }
        "dialog:select_folder" => {
            let path = desktop_service.select_folder()?;
            Ok(json!(path))
        }
        _ => Err(format!("Unsupported desktop operation: {}", op)),
    }
}

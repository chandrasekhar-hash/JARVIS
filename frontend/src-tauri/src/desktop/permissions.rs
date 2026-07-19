use serde_json::Value;
use tauri::AppHandle;
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};

pub struct PermissionManager {
    app_handle: AppHandle,
}

impl PermissionManager {
    pub fn new(app_handle: AppHandle) -> Self {
        PermissionManager { app_handle }
    }

    pub async fn verify_permission(&self, op: &str, args: &Value) -> Result<(), String> {
        let safety_level = match op {
            "window:list" | "process:list" | "dialog:select_file" | "dialog:select_folder" => "safe",
            "window:control" | "clipboard:read" | "clipboard:write" | "system:notify" => "sensitive",
            "process:terminate" => "destructive",
            _ => "unknown",
        };

        match safety_level {
            "safe" => {
                Ok(())
            }
            "sensitive" => {
                log::info!("[Permissions] Sensitive operation allowed: {}", op);
                Ok(())
            }
            "destructive" => {
                log::warn!("[Permissions] Destructive operation requested: {}. Prompting native dialog...", op);

                let msg = match op {
                    "process:terminate" => {
                        let name = args.get("name").and_then(|n| n.as_str()).unwrap_or("Unknown");
                        let pid = args.get("pid").and_then(|p| p.as_u64()).unwrap_or(0);
                        format!("JARVIS is requesting to terminate process '{}' (PID: {}). Do you want to allow this action?", name, pid)
                    }
                    _ => format!("JARVIS is requesting to execute a destructive operation ({}). Do you want to allow this action?", op),
                };

                let handle = self.app_handle.clone();
                let confirmed = tauri::async_runtime::spawn_blocking(move || {
                    handle.dialog()
                        .message(&msg)
                        .title("Destructive Action Confirmation")
                        .kind(MessageDialogKind::Warning)
                        .blocking_show()
                }).await.map_err(|e| format!("Dialog thread spawn failed: {}", e))?;

                if confirmed {
                    log::info!("[Permissions] Destructive operation approved by user: {}", op);
                    Ok(())
                } else {
                    log::warn!("[Permissions] Destructive operation denied by user: {}", op);
                    Err("Permission Denied: Destructive action rejected by user.".to_string())
                }
            }
            _ => {
                Err(format!("Permission Denied: Unknown desktop operation safety level for '{}'.", op))
            }
        }
    }
}

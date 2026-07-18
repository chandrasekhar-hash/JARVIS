use std::process::{Command, Child};
use std::sync::Mutex;
use std::os::windows::process::CommandExt;
use log::{info, error};
use crate::config::RuntimeConfig;

const CREATE_NO_WINDOW: u32 = 0x08000000;

pub struct BackendManager {
    child: Mutex<Option<Child>>,
}

impl BackendManager {
    pub fn new() -> Self {
        BackendManager {
            child: Mutex::new(None),
        }
    }

    pub fn start(&self, config: &RuntimeConfig) -> Result<(), String> {
        let mut guard = self.child.lock().unwrap();
        if guard.is_some() {
            return Err("Backend process is already running".to_string());
        }

        let python_path = &config.python_path;
        let script_path = &config.backend_script;

        if !script_path.exists() {
            return Err(format!("Backend script not found at {:?}", script_path));
        }

        info!(
            "[BackendManager] Spawning process: executable={:?} script={:?}",
            python_path, script_path
        );

        // Spawn python subprocess with CREATE_NO_WINDOW flag to prevent console popup
        let spawn_res = Command::new(python_path)
            .arg(script_path)
            .creation_flags(CREATE_NO_WINDOW)
            .spawn();

        match spawn_res {
            Ok(child_proc) => {
                info!("[BackendManager] Successfully spawned process with PID={}", child_proc.id());
                *guard = Some(child_proc);
                Ok(())
            }
            Err(e) => {
                let err_msg = format!("Failed to spawn process: {:?}", e);
                error!("[BackendManager] {}", err_msg);
                Err(err_msg)
            }
        }
    }

    pub fn stop(&self) {
        let mut guard = self.child.lock().unwrap();
        if let Some(mut child_proc) = guard.take() {
            let pid = child_proc.id();
            info!("[BackendManager] Terminating process PID={}", pid);
            match child_proc.kill() {
                Ok(_) => {
                    // Wait for process to clean up
                    let _ = child_proc.wait();
                    info!("[BackendManager] Process PID={} terminated successfully", pid);
                }
                Err(e) => {
                    error!("[BackendManager] Failed to kill process PID={}: {:?}", pid, e);
                }
            }
        }
    }

    pub fn is_alive(&self) -> bool {
        let mut guard = self.child.lock().unwrap();
        if let Some(ref mut child_proc) = *guard {
            // Check if process has exited without blocking
            match child_proc.try_wait() {
                Ok(None) => true,       // Still running
                Ok(Some(status)) => {   // Exited
                    info!("[BackendManager] Process exited with status: {:?}", status);
                    *guard = None;
                    false
                }
                Err(e) => {
                    error!("[BackendManager] Error checking process status: {:?}", e);
                    *guard = None;
                    false
                }
            }
        } else {
            false
        }
    }
}

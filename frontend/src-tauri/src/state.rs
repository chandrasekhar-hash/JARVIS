use serde::Serialize;
use std::sync::Mutex;
use tauri::{AppHandle, Emitter};
use log::{info, warn, error};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum RuntimeState {
    Boot,
    LaunchingBackend,
    WaitingForHealth,
    Ready,
    Restarting,
    Failed,
    Shutdown,
}

pub struct StateMachine {
    current_state: Mutex<RuntimeState>,
    pub app_handle: Mutex<Option<AppHandle>>,
}

impl StateMachine {
    pub fn new() -> Self {
        StateMachine {
            current_state: Mutex::new(RuntimeState::Boot),
            app_handle: Mutex::new(None),
        }
    }

    pub fn set_app_handle(&self, handle: AppHandle) {
        let mut guard = self.app_handle.lock().unwrap();
        *guard = Some(handle);
    }

    pub fn get_state(&self) -> RuntimeState {
        *self.current_state.lock().unwrap()
    }

    pub fn transition(&self, next_state: RuntimeState) {
        let mut state_guard = self.current_state.lock().unwrap();
        let prev_state = *state_guard;

        // 1. Avoid duplicate state broadcasts
        if prev_state == next_state {
            return;
        }

        // 2. Enforce state transition rules (no transitions out of terminal state Shutdown or Failed)
        if prev_state == RuntimeState::Shutdown && next_state != RuntimeState::Shutdown {
            warn!("[StateMachine] Invalid state transition rejected: from={:?} to={:?}", prev_state, next_state);
            return;
        }

        *state_guard = next_state;
        info!("[StateMachine] state_transition: from={:?}, to={:?}", prev_state, next_state);

        // 3. Emit structured change event to React frontend
        let app_handle_guard = self.app_handle.lock().unwrap();
        if let Some(ref handle) = *app_handle_guard {
            let payload = serde_json::json!({
                "state": format!("{:?}", next_state).to_uppercase(),
                "previous": format!("{:?}", prev_state).to_uppercase()
            });
            if let Err(e) = handle.emit("runtime-state-change", payload) {
                error!("[StateMachine] Failed to emit event: {:?}", e);
            }
        }
    }
}

mod config;
mod state;
mod manager;
mod monitor;
mod supervisor;
mod ipc;

use std::sync::Arc;
use tauri::{Manager, RunEvent};
use log::info;
use crate::config::RuntimeConfig;
use crate::state::{RuntimeState, StateMachine};
use crate::manager::BackendManager;
use crate::monitor::HealthMonitor;
use crate::supervisor::ProcessSupervisor;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default();

    // Set up structured logging plugin in debug mode
    if cfg!(debug_assertions) {
        builder = builder.plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        );
    }

    let app = builder
        .setup(|app| {
            info!("[Setup] Initializing JARVIS Desktop Runtime Phase 1 subsystems...");

            // 1. Initialize Centralized Configuration
            let config = Arc::new(RuntimeConfig::new());

            // 2. Initialize Core Subsystems
            let manager = Arc::new(BackendManager::new());
            let monitor = Arc::new(HealthMonitor::new());
            let state_machine = Arc::new(StateMachine::new());

            // Bind app handle for UI events
            state_machine.set_app_handle(app.handle().clone());

            // Register with Tauri's State Management
            app.manage(config.clone());
            app.manage(manager.clone());
            app.manage(state_machine.clone());

            // 3. Initialize and Start Process Supervisor Loop
            let supervisor = Arc::new(ProcessSupervisor::new(
                config,
                manager,
                monitor,
                state_machine,
            ));
            supervisor.start_supervision_loop();

            info!("[Setup] Subsystems initialized and supervisor loop spawned.");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ipc::send_chat_message,
            ipc::get_system_info,
            ipc::get_tts_audio
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // 4. Register clean exit hook to prevent orphan Python backend processes
    app.run(move |app_handle, event| {
        match event {
            RunEvent::ExitRequested { .. } => {
                info!("[ExitHook] ExitRequested event received.");
            }
            RunEvent::Exit => {
                info!("[ExitHook] Exit event received. Stopping subprocesses...");
                if let Some(state_machine) = app_handle.try_state::<Arc<StateMachine>>() {
                    state_machine.transition(RuntimeState::Shutdown);
                }
                if let Some(manager) = app_handle.try_state::<Arc<BackendManager>>() {
                    manager.stop();
                }
                info!("[ExitHook] Subprocesses stopped cleanly.");
            }
            RunEvent::WindowEvent { label, event: win_event, .. } => {
                info!("[ExitHook] WindowEvent for window '{}': {:?}", label, win_event);
            }
            _ => {}
        }
    });
}

mod config;
mod state;
mod manager;
mod monitor;
mod supervisor;
mod ipc;
mod desktop;

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

    builder = builder
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new()
            .with_handler(move |app, shortcut, event| {
                use tauri_plugin_global_shortcut::{Shortcut, ShortcutState};
                if event.state() == ShortcutState::Released {
                    if let Ok(target) = "Alt+Space".parse::<Shortcut>() {
                        if shortcut == &target {
                            if let Some(window) = app.get_webview_window("main") {
                                let is_visible = window.is_visible().unwrap_or(false);
                                if is_visible {
                                    let _ = window.hide();
                                } else {
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            }
                        }
                    }
                }
            })
            .build()
        );

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

            // 2b. Initialize Platform-independent Desktop Service
            #[cfg(target_os = "windows")]
            let desktop_service: Arc<dyn crate::desktop::service::DesktopService + Send + Sync> = Arc::new(crate::desktop::windows::WindowsDesktopService::new(app.handle().clone()));
            #[cfg(not(target_os = "windows"))]
            let desktop_service: Arc<dyn crate::desktop::service::DesktopService + Send + Sync> = Arc::new(crate::desktop::mock::MockDesktopService::new(app.handle().clone()));
            app.manage(desktop_service);

            // 2c. Initialize Permission Manager
            let perm_manager = Arc::new(crate::desktop::permissions::PermissionManager::new(app.handle().clone()));
            app.manage(perm_manager);

            // 2d. Register Global Shortcut (Alt + Space)
            use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut};
            if let Ok(shortcut) = "Alt+Space".parse::<Shortcut>() {
                let _ = app.global_shortcut().register(shortcut);
            }

            // 2e. Setup System Tray Menu and Icon
            use tauri::tray::TrayIconBuilder;
            use tauri::menu::{Menu, MenuItem};

            let tray_menu = Menu::with_items(app, &[
                &MenuItem::with_id(app, "show", "Show JARVIS", true, None::<&str>).unwrap(),
                &MenuItem::with_id(app, "hide", "Hide JARVIS", true, None::<&str>).unwrap(),
                &MenuItem::with_id(app, "exit", "Exit", true, None::<&str>).unwrap(),
            ]).unwrap();

            let icon = app.default_window_icon().cloned();
            let mut tray_builder = TrayIconBuilder::new()
                .menu(&tray_menu)
                .on_menu_event(move |app, event| {
                    match event.id.as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "hide" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.hide();
                            }
                        }
                        "exit" => {
                            app.exit(0);
                        }
                        _ => {}
                    }
                });

            if let Some(ref ico) = icon {
                tray_builder = tray_builder.icon(ico.clone());
            }
            let _tray = tray_builder.build(app).expect("Failed to build tray");

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
            ipc::get_tts_audio,
            desktop::dispatcher::dispatch_desktop_operation
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

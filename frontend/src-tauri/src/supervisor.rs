use std::sync::Arc;
use std::time::Duration;
use tokio::time::sleep;
use log::{info, error, warn};
use crate::config::RuntimeConfig;
use crate::manager::BackendManager;
use crate::monitor::HealthMonitor;
use crate::state::{RuntimeState, StateMachine};

pub struct ProcessSupervisor {
    config: Arc<RuntimeConfig>,
    manager: Arc<BackendManager>,
    monitor: Arc<HealthMonitor>,
    state_machine: Arc<StateMachine>,
}

impl ProcessSupervisor {
    pub fn new(
        config: Arc<RuntimeConfig>,
        manager: Arc<BackendManager>,
        monitor: Arc<HealthMonitor>,
        state_machine: Arc<StateMachine>,
    ) -> Self {
        ProcessSupervisor {
            config,
            manager,
            monitor,
            state_machine,
        }
    }

    pub fn start_supervision_loop(self: Arc<Self>) {
        tauri::async_runtime::spawn(async move {
            let mut retry_count = 0;
            
            loop {
                let current = self.state_machine.get_state();
                if current == RuntimeState::Shutdown {
                    info!("[Supervisor] Shutdown state detected. Stopping supervisor loop.");
                    break;
                }

                match current {
                    RuntimeState::Boot => {
                        self.state_machine.transition(RuntimeState::LaunchingBackend);
                    }
                    RuntimeState::LaunchingBackend => {
                        info!("[Supervisor] Launching backend service. Attempt #{}", retry_count + 1);
                        match self.manager.start(&self.config) {
                            Ok(_) => {
                                self.state_machine.transition(RuntimeState::WaitingForHealth);
                            }
                            Err(e) => {
                                error!("[Supervisor] Failed to start backend: {}", e);
                                self.handle_failure(&mut retry_count).await;
                            }
                        }
                    }
                    RuntimeState::WaitingForHealth => {
                        let is_healthy = self.monitor.check_health(&self.config.health_url).await;
                        if is_healthy {
                            info!("[Supervisor] Service is healthy and online!");
                            retry_count = 0; // reset retry count
                            self.state_machine.transition(RuntimeState::Ready);
                        } else {
                            if !self.manager.is_alive() {
                                warn!("[Supervisor] Backend process died while waiting for health check");
                                self.handle_failure(&mut retry_count).await;
                            } else {
                                sleep(Duration::from_millis(200)).await;
                            }
                        }
                    }
                    RuntimeState::Ready => {
                        if std::env::var("JARVIS_TEST_SHUTDOWN").is_ok() {
                            info!("[Supervisor] JARVIS_TEST_SHUTDOWN env set. Triggering clean exit in 3s...");
                            sleep(Duration::from_secs(3)).await;
                            let app_handle_guard = self.state_machine.app_handle.lock().unwrap();
                            if let Some(ref handle) = *app_handle_guard {
                                info!("[Supervisor] Calling app_handle.exit(0) for clean shutdown.");
                                handle.exit(0);
                            }
                            break;
                        }

                        if !self.manager.is_alive() {
                            warn!("[Supervisor] Backend process died unexpectedly from READY state!");
                            self.handle_failure(&mut retry_count).await;
                        } else {
                            sleep(Duration::from_secs(1)).await;
                        }
                    }
                    RuntimeState::Restarting => {
                        sleep(Duration::from_millis(200)).await;
                    }
                    RuntimeState::Failed => {
                        error!("[Supervisor] Terminal Failed state. Supervisor suspended.");
                        sleep(Duration::from_secs(5)).await;
                    }
                    RuntimeState::Shutdown => {
                        info!("[Supervisor] Shutdown state. Exiting supervision loop.");
                        break;
                    }
                }
            }
        });
    }

    async fn handle_failure(&self, retry_count: &mut usize) {
        if *retry_count >= self.config.max_restart_retries {
            error!("[Supervisor] Max restart retries reached. Transitioning to FAILED.");
            self.state_machine.transition(RuntimeState::Failed);
            return;
        }

        self.state_machine.transition(RuntimeState::Restarting);

        // Compute exponential backoff: delay = min(base_delay * 2^retry, max_delay)
        let delay_ms = std::cmp::min(
            self.config.base_retry_delay_ms * (2_u64.pow(*retry_count as u32)),
            self.config.max_retry_delay_ms,
        );

        warn!(
            "[Supervisor] Scheduling restart. Backing off for {}ms (retry {}/{})",
            delay_ms,
            *retry_count + 1,
            self.config.max_restart_retries
        );

        sleep(Duration::from_millis(delay_ms)).await;
        *retry_count += 1;
        self.state_machine.transition(RuntimeState::LaunchingBackend);
    }
}

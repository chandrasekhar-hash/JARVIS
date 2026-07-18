use reqwest::Client;
use std::time::Duration;
use log::debug;

pub struct HealthMonitor {
    client: Client,
}

impl HealthMonitor {
    pub fn new() -> Self {
        HealthMonitor {
            client: Client::builder()
                .timeout(Duration::from_secs(1))
                .build()
                .unwrap_or_else(|_| Client::new()),
        }
    }

    pub async fn check_health(&self, url: &str) -> bool {
        match self.client.get(url).send().await {
            Ok(resp) => {
                if resp.status().is_success() {
                    debug!("[HealthMonitor] Health check succeeded: {}", url);
                    true
                } else {
                    debug!("[HealthMonitor] Health check returned non-200 status: {}", resp.status());
                    false
                }
            }
            Err(e) => {
                debug!("[HealthMonitor] Health check connection failed: {:?}", e.to_string());
                false
            }
        }
    }
}

use std::path::PathBuf;
use std::env;

#[derive(Debug, Clone)]
pub struct RuntimeConfig {
    pub python_path: PathBuf,
    pub backend_script: PathBuf,
    pub backend_host: String,
    pub backend_port: u16,
    pub health_url: String,
    pub max_restart_retries: usize,
    pub base_retry_delay_ms: u64,
    pub max_retry_delay_ms: u64,
}

impl RuntimeConfig {
    pub fn new() -> Self {
        // Resolve python executable path
        let python_path = if let Ok(val) = env::var("JARVIS_PYTHON") {
            PathBuf::from(val)
        } else {
            // Default to local workspace .venv if present
            let local_venv = PathBuf::from("d:\\JARVIS\\Backend\\.venv\\Scripts\\python.exe");
            if local_venv.exists() {
                local_venv
            } else {
                PathBuf::from("python")
            }
        };

        // Resolve backend script path
        let backend_script = if let Ok(val) = env::var("JARVIS_BACKEND_SCRIPT") {
            PathBuf::from(val)
        } else {
            PathBuf::from("d:\\JARVIS\\Backend\\main.py")
        };

        // Host and Port configuration
        let backend_host = env::var("JARVIS_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
        let backend_port = env::var("JARVIS_PORT")
            .ok()
            .and_then(|p| p.parse().ok())
            .unwrap_or(8000);

        let health_url = format!("http://{}:{}/health", backend_host, backend_port);

        // Supervisor Retry Metrics
        let max_restart_retries = env::var("JARVIS_MAX_RETRIES")
            .ok()
            .and_then(|r| r.parse().ok())
            .unwrap_or(5);

        let base_retry_delay_ms = env::var("JARVIS_BASE_RETRY_DELAY")
            .ok()
            .and_then(|d| d.parse().ok())
            .unwrap_or(200);

        let max_retry_delay_ms = env::var("JARVIS_MAX_RETRY_DELAY")
            .ok()
            .and_then(|d| d.parse().ok())
            .unwrap_or(5000);

        RuntimeConfig {
            python_path,
            backend_script,
            backend_host,
            backend_port,
            health_url,
            max_restart_retries,
            base_retry_delay_ms,
            max_retry_delay_ms,
        }
    }
}

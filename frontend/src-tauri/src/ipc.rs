use tauri::{AppHandle, Emitter};
use serde::{Serialize, Deserialize};
use reqwest::Client;
use std::time::Duration;
use futures_util::StreamExt;
use log::{info, error};

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequest {
    pub message: String,
    pub voice: String,
    pub language: String,
    pub tts_language: String,
    pub assistant_name: String,
    pub creator: String,
}

#[tauri::command]
pub async fn send_chat_message(
    app: AppHandle,
    payload: ChatRequest,
) -> Result<(), String> {
    info!("[IPC] Forwarding chat request: message={:?}", payload.message);
    let client = Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let url = "http://127.0.0.1:8000/api/chat";
    let resp = client.post(url)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Failed to send request to FastAPI: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("FastAPI backend returned error: {}", resp.status()));
    }

    let mut stream = resp.bytes_stream();
    let mut buffer = Vec::new();

    while let Some(chunk_res) = stream.next().await {
        let chunk = chunk_res.map_err(|e| format!("SSE Stream error: {}", e))?;
        buffer.extend_from_slice(&chunk);

        // Process line-by-line from the buffer
        while let Some(newline_idx) = buffer.iter().position(|&b| b == b'\n') {
            let line_bytes = buffer.drain(..=newline_idx).collect::<Vec<u8>>();
            let line = String::from_utf8_lossy(&line_bytes);
            let trimmed = line.trim();

            if trimmed.starts_with("data:") {
                let data_str = trimmed["data:".len()..].trim();
                if let Ok(json_val) = serde_json::from_str::<serde_json::Value>(data_str) {
                    if let Err(e) = app.emit("chat-token", json_val) {
                        error!("[IPC] Failed to emit chat-token event: {:?}", e);
                    }
                }
            }
        }
    }

    Ok(())
}

#[tauri::command]
pub async fn get_system_info() -> Result<serde_json::Value, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|e| e.to_string())?;

    let url = "http://127.0.0.1:8000/api/system_info";
    let resp = client.get(url)
        .send()
        .await
        .map_err(|e| format!("Failed to request system_info: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("FastAPI system_info returned error: {}", resp.status()));
    }

    let json_val = resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse system_info JSON: {}", e))?;

    Ok(json_val)
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TTSRequest {
    pub text: String,
    pub voice: String,
    pub language: String,
}

#[tauri::command]
pub async fn get_tts_audio(payload: TTSRequest) -> Result<serde_json::Value, String> {
    let client = Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let url = "http://127.0.0.1:8000/api/tts";
    let resp = client.post(url)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Failed to request TTS: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("FastAPI tts returned error: {}", resp.status()));
    }

    let json_val = resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse TTS JSON: {}", e))?;

    Ok(json_val)
}

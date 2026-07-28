import time
import logging
import threading
from typing import Callable, List, Optional, Dict, Any

from Backend.voice.wakeword.settings import wake_word_settings, WakeWordSettings
from Backend.voice.wakeword.metrics import wake_word_metrics, WakeWordMetrics
from Backend.voice.wakeword.audio_preprocessor import audio_preprocessor, AudioPreprocessor
from Backend.voice.wakeword.noise_filter import noise_filter, NoiseFilter
from Backend.voice.wakeword.keyword_manager import keyword_manager, KeywordManager
from Backend.voice.wakeword.confidence import confidence_engine, ConfidenceEngine
from Backend.voice.wakeword.detector import wake_word_detector, WakeWordDetector
from Backend.voice.wakeword.listener import audio_listener, AudioListener
from Backend.voice.wakeword.health import health_monitor, HealthMonitor
from Backend.voice.wakeword.events import (
    WakeWordDetectedEvent, WakeWordRejectedEvent,
    EngineStartedEvent, EngineStoppedEvent,
    MicrophoneDisconnectedEvent, EngineRecoveredEvent
)
from Backend.voice.wakeword.exceptions import WakeWordError, MicrophoneDisconnectedError

logger = logging.getLogger("JARVIS_WakeWordEngine")


class WakeWordEngine:
    """
    Master Wake Word Engine orchestrating always-listening continuous audio ingestion,
    volume normalization, spectral noise filtering, acoustic detection, confidence evaluation,
    event dispatches, diagnostic metrics, health reporting, and thread-safe automatic recovery.
    """

    def __init__(
        self,
        settings: Optional[WakeWordSettings] = None,
        kw_manager: Optional[KeywordManager] = None,
        conf_engine: Optional[ConfidenceEngine] = None,
        preprocessor: Optional[AudioPreprocessor] = None,
        filter_engine: Optional[NoiseFilter] = None,
        detector_engine: Optional[WakeWordDetector] = None,
        listener_engine: Optional[AudioListener] = None,
        health_eng: Optional[HealthMonitor] = None,
        metrics_eng: Optional[WakeWordMetrics] = None
    ):
        self.settings = settings or wake_word_settings
        self.kw_manager = kw_manager or keyword_manager
        self.conf_engine = conf_engine or confidence_engine
        self.preprocessor = preprocessor or audio_preprocessor
        self.filter_engine = filter_engine or noise_filter
        self.detector_engine = detector_engine or wake_word_detector
        self.listener_engine = listener_engine or audio_listener
        self.health_eng = health_eng or health_monitor
        self.metrics_eng = metrics_eng or wake_word_metrics

        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.Lock()
        self._is_running = False

    def register_detection_callback(self, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            self._callbacks.append(callback)
            logger.info("Registered WakeWordEngine detection callback.")

    def start(self):
        with self._lock:
            if self._is_running:
                logger.warning("WakeWordEngine is already running.")
                return

            self._is_running = True
            self.listener_engine.frame_callback = self._on_audio_frame
            self.listener_engine.error_callback = self._on_listener_error
            self.listener_engine.start()

            self.health_eng.set_status("RUNNING", mic_connected=True)
            logger.info(f"WakeWordEngine STARTED with primary wake word '{self.kw_manager.primary_keyword}'.")

            # Dispatch EngineStarted event
            evt = EngineStartedEvent(primary_keyword=self.kw_manager.primary_keyword)

    def stop(self):
        with self._lock:
            if not self._is_running:
                return

            self._is_running = False
            self.listener_engine.stop()
            self.health_eng.set_status("STOPPED", mic_connected=False)
            logger.info("WakeWordEngine STOPPED cleanly.")

            # Dispatch EngineStopped event
            evt = EngineStoppedEvent()

    def restart(self):
        logger.info("Restarting WakeWordEngine...")
        self.stop()
        time.sleep(0.5)
        self.start()

    def process_pcm_frame(self, pcm_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Processes a raw PCM frame directly and returns detection metadata if activated.
        """
        self.metrics_eng.record_frame()

        # 1. Preprocess frame
        audio, is_silent = self.preprocessor.preprocess_frame(pcm_bytes)

        if is_silent:
            # Update background noise profile during silence
            self.filter_noise_profile_update(audio)
            return None

        # 2. Filter noise
        clean_audio = self.filter_engine.filter_noise(audio)

        # 3. Detect wake word candidate
        match_meta = self.detector_engine.detect_in_frame(clean_audio, self.settings.sample_rate)

        if match_meta:
            self.metrics_eng.record_detection(match_meta["keyword"], match_meta["confidence"])

            # Dispatch to registered callbacks
            with self._lock:
                for cb in self._callbacks:
                    try:
                        cb(match_meta)
                    except Exception as e:
                        logger.error(f"Error executing detection callback: {e}")

            return match_meta

        return None

    def filter_noise_profile_update(self, audio: np.ndarray):
        try:
            self.filter_engine.update_noise_profile(audio)
        except Exception as e:
            logger.debug(f"Error updating noise profile: {e}")

    def _on_audio_frame(self, pcm_bytes: bytes):
        if not self._is_running:
            return
        try:
            self.process_pcm_frame(pcm_bytes)
        except Exception as e:
            logger.error(f"Error in WakeWordEngine frame loop: {e}")
            self.metrics_eng.record_error()

    def _on_listener_error(self, exc: Exception):
        logger.error(f"Listener error encountered: {exc}")
        self.metrics_eng.record_error()
        self.health_eng.set_status("DEGRADED", mic_connected=False)

        if self.settings.auto_recovery and self._is_running:
            logger.info("Attempting automatic engine recovery...")
            self.health_eng.record_recovery()
            threading.Thread(target=self.restart, daemon=True).start()

    def get_health(self) -> Dict[str, Any]:
        return self.health_eng.get_health_report()


wake_word_engine = WakeWordEngine()

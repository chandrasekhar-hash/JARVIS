"""
Audio Processing Pipeline Orchestrator for J.A.R.V.I.S. Phase V1.5 Audio Intelligence Engine.
Executes Noise Suppression, Echo Cancellation, AGC, Normalization, Quality Analysis, and Confidence Estimation.
"""
import time
import logging
from typing import Optional

from .config import AudioConfig, audio_config
from .models import (
    AudioFrame,
    EnhancedAudioFrame,
    AudioQualityReport,
    AudioConfidence,
    ProcessingResult,
)
from .interfaces import (
    INoiseSuppressor,
    IEchoCanceller,
    IAutomaticGainController,
    IAudioNormalizer,
    IAudioQualityAnalyzer,
    IAudioConfidenceEstimator,
)
from .noise_suppression import NoiseSuppressor
from .echo_cancellation import EchoCanceller
from .gain_control import AutomaticGainController
from .normalization import AudioNormalizer
from .quality_analyzer import AudioQualityAnalyzer
from .confidence import AudioConfidenceEstimator
from .metrics import audio_metrics, AudioMetrics
from brain.event_bus import event_bus, EventBus
from .events import (
    AudioProcessingStarted,
    NoiseReductionCompleted,
    EchoCancellationCompleted,
    GainControlCompleted,
    AudioNormalizationCompleted,
    AudioQualityComputed,
    AudioConfidenceComputed,
    EnhancedAudioReady,
    AudioProcessingFailed,
)

logger = logging.getLogger("JARVIS_AudioPipeline")


class AudioProcessingPipeline:
    """
    Sequentially processes incoming AudioFrames through configured enhancement stages.
    """

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        noise_suppressor: Optional[INoiseSuppressor] = None,
        echo_canceller: Optional[IEchoCanceller] = None,
        gain_controller: Optional[IAutomaticGainController] = None,
        normalizer: Optional[IAudioNormalizer] = None,
        quality_analyzer: Optional[IAudioQualityAnalyzer] = None,
        confidence_estimator: Optional[IAudioConfidenceEstimator] = None,
        bus: Optional[EventBus] = None,
    ):
        self.config = config or audio_config
        self.event_bus = bus or event_bus
        self.metrics = audio_metrics

        self.noise_suppressor = noise_suppressor or NoiseSuppressor()
        self.echo_canceller = echo_canceller or EchoCanceller()
        self.gain_controller = gain_controller or AutomaticGainController(target_rms=self.config.target_rms_db * -250.0)
        self.normalizer = normalizer or AudioNormalizer()
        self.quality_analyzer = quality_analyzer or AudioQualityAnalyzer()
        self.confidence_estimator = confidence_estimator or AudioConfidenceEstimator()

    async def process_frame(self, frame: AudioFrame, session_id: str = "default_session") -> ProcessingResult:
        """Processes an AudioFrame through the complete pipeline sequentially."""
        start_time = time.perf_counter()
        curr_frame = frame

        # Emit AudioProcessingStarted
        start_evt = AudioProcessingStarted(session_id=session_id, frame_id=frame.frame_id)
        self.event_bus.emit("AudioProcessingStarted", **start_evt.__dict__)

        snr_gain_db = 0.0
        echo_attenuation_db = 0.0
        gain_applied_db = 0.0

        try:
            # 1. Noise Suppression
            if self.config.noise_suppression_enabled and self.noise_suppressor:
                curr_frame, snr_gain_db = self.noise_suppressor.suppress_noise(curr_frame)
                self.metrics.record_snr_gain(snr_gain_db)
                noise_evt = NoiseReductionCompleted(session_id=session_id, frame_id=frame.frame_id, snr_gain_db=snr_gain_db)
                self.event_bus.emit("NoiseReductionCompleted", **noise_evt.__dict__)

            # 2. Echo Cancellation
            if self.config.echo_cancellation_enabled and self.echo_canceller:
                curr_frame, echo_attenuation_db = self.echo_canceller.cancel_echo(curr_frame)
                echo_evt = EchoCancellationCompleted(session_id=session_id, frame_id=frame.frame_id, echo_attenuation_db=echo_attenuation_db)
                self.event_bus.emit("EchoCancellationCompleted", **echo_evt.__dict__)

            # 3. Automatic Gain Control (AGC)
            if self.config.agc_enabled and self.gain_controller:
                curr_frame, gain_applied_db = self.gain_controller.apply_gain(curr_frame)
                self.metrics.record_gain_adjustment(gain_applied_db)
                agc_evt = GainControlCompleted(session_id=session_id, frame_id=frame.frame_id, gain_applied_db=gain_applied_db)
                self.event_bus.emit("GainControlCompleted", **agc_evt.__dict__)

            # 4. Audio Normalization
            if self.config.normalization_enabled and self.normalizer:
                curr_frame = self.normalizer.normalize(curr_frame)
                norm_evt = AudioNormalizationCompleted(session_id=session_id, frame_id=frame.frame_id)
                self.event_bus.emit("AudioNormalizationCompleted", **norm_evt.__dict__)

            # 5. Quality Analysis
            quality_report = AudioQualityReport()
            if self.config.quality_analysis_enabled and self.quality_analyzer:
                quality_report = self.quality_analyzer.analyze_quality(curr_frame)
                self.metrics.record_quality_score(quality_report.quality_score)
                qual_evt = AudioQualityComputed(session_id=session_id, frame_id=frame.frame_id, quality_score=quality_report.quality_score)
                self.event_bus.emit("AudioQualityComputed", **qual_evt.__dict__)

            # 6. Confidence Estimation
            confidence = AudioConfidence()
            if self.config.confidence_estimation_enabled and self.confidence_estimator:
                confidence = self.confidence_estimator.estimate_confidence(curr_frame, quality_report)
                self.metrics.record_confidence_score(confidence.combined_score)
                conf_evt = AudioConfidenceComputed(session_id=session_id, frame_id=frame.frame_id, combined_score=confidence.combined_score)
                self.event_bus.emit("AudioConfidenceComputed", **conf_evt.__dict__)

            # Build EnhancedAudioFrame
            enhanced_frame = EnhancedAudioFrame(
                frame_id=frame.frame_id,
                original_frame=frame,
                enhanced_data=curr_frame.data,
                snr_db=quality_report.snr_db,
                rms_level=quality_report.speech_energy,
                gain_applied_db=gain_applied_db,
            )

            # Record Latency
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.metrics.record_latency(latency_ms)
            self.metrics.total_frames_processed += 1

            # Emit EnhancedAudioReady Event
            ready_evt = EnhancedAudioReady(
                session_id=session_id,
                frame_id=frame.frame_id,
                enhanced_frame=enhanced_frame,
                quality_report=quality_report,
                confidence=confidence,
            )
            self.event_bus.emit("EnhancedAudioReady", **ready_evt.__dict__)

            return ProcessingResult(
                success=True,
                frame_id=frame.frame_id,
                enhanced_frame=enhanced_frame,
                quality_report=quality_report,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"[AudioPipeline] Error processing frame '{frame.frame_id}': {e}")
            self.metrics.total_processing_failures += 1
            fail_evt = AudioProcessingFailed(session_id=session_id, frame_id=frame.frame_id, error_message=str(e))
            self.event_bus.emit("AudioProcessingFailed", **fail_evt.__dict__)

            return ProcessingResult(
                success=False,
                frame_id=frame.frame_id,
                error=str(e),
            )

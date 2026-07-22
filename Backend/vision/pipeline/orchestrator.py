import time
from typing import Optional, Tuple, Dict, Any
from vision.models.capture_models import CaptureTarget, CaptureFrame
from vision.models.ocr_models import OCRResult
from vision.models.ui_models import UIObservation
from vision.models.scene_models import SceneObservation
from vision.capture.engine import capture_engine
from vision.analysis.ocr import ocr_engine
from vision.analysis.ui import ui_analyzer
from vision.analysis.scene import scene_analyzer
from brain.event_bus import event_bus
from tools.logger import log_structured, backend_log

class VisionPipelineOrchestrator:
    def run_snapshot(
        self,
        target: Optional[CaptureTarget] = None
    ) -> Optional[Tuple[CaptureFrame, OCRResult, UIObservation, SceneObservation]]:
        """
        Executes a complete single-pass Vision snapshot pipeline:
        Capture -> OCR -> UI Analysis -> Scene Understanding -> Event Emissions.
        Returns a tuple of all 4 observation layers, or None if capture is denied.
        """
        t0 = time.time()
        event_bus.emit("VisionStarted", mode="snapshot")

        # 1. Screen Capture
        frame = capture_engine.capture_frame(target)
        if not frame:
            log_structured(backend_log, "WARNING", "[VisionOrchestrator] Snapshot pipeline aborted: Capture permission denied.")
            event_bus.emit("VisionStopped", reason="permission_denied")
            return None

        event_bus.emit("FrameCaptured", frame_id=frame.frame_id, resolution=frame.resolution)

        # 2. OCR Text Extraction (Milestone 3.2)
        ocr_res = ocr_engine.extract_text_from_frame(frame)
        event_bus.emit("OCRCompleted", frame_id=frame.frame_id, text_count=len(ocr_res.detected_elements))

        # 3. UI Layout & Element Understanding (Milestone 3.3)
        ui_obs = ui_analyzer.analyze_frame(frame)
        event_bus.emit("UIAnalysisCompleted", frame_id=frame.frame_id, element_count=len(ui_obs.ui_elements))

        # 4. Scene & Workflow Understanding (Milestone 3.4)
        scene_obs = scene_analyzer.analyze_frame(frame)
        event_bus.emit("SceneAnalysisCompleted", 
            frame_id=frame.frame_id,
            headline=scene_obs.summary.headline,
            workflow=scene_obs.summary.detected_workflow
        )

        event_bus.emit("VisionObservationReady", 
            observation_id=scene_obs.observation_id,
            headline=scene_obs.summary.headline
        )

        elapsed = time.time() - t0
        log_structured(backend_log, "INFO", f"[VisionOrchestrator] Snapshot pipeline executed in {elapsed:.3f}s")
        return (frame, ocr_res, ui_obs, scene_obs)

vision_orchestrator = VisionPipelineOrchestrator()

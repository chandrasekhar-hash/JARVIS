from typing import List, Dict, Any, Optional

from intelligence.vision.models import VisionRequest, VisionResult, VisionImageItem
from intelligence.vision.providers.gemini_vision import GeminiVisionProvider
from intelligence.vision.multi_image.models import MultiImageResult
from intelligence.vision.multi_image.context_builder import multi_image_context_builder
from intelligence.vision.multi_image.instruction_builder import build_multi_image_instruction
from intelligence.vision.multi_image.relationship_builder import relationship_builder
from tools.telemetry import log_structured, backend_log

class MultiImageService:
    """
    MultiImage Service Facade (V6).
    Orchestrates:
    Images -> MultiImageContextBuilder (Context)
           -> InstructionBuilder (Instruction)
           -> GeminiVisionProvider (Multimodal Reasoning)
           -> RelationshipBuilder (Parser / Normalizer)
           -> Structured MultiImageResult & VisionResult
    """

    def __init__(self):
        self.provider = GeminiVisionProvider()

    async def analyze_multi_images(self, request: VisionRequest) -> VisionResult:
        if not request.images or len(request.images) < 2:
            raise ValueError("MultiImage analysis requires at least 2 images.")

        log_structured(backend_log, "INFO", f"[MultiImageService] Building context for {len(request.images)} images...")
        
        # 1. Prepare Context (No visual inference, only context metadata & duplicate/OCR detection)
        context = await multi_image_context_builder.build_context(
            images=request.images,
            prompt=request.prompt
        )

        # 2. Build Multi-Image System Instruction for Gemini Vision
        system_instruction = build_multi_image_instruction(
            context=context,
            user_prompt=request.prompt
        )

        # 3. Construct Vision Request for Gemini
        vision_req = VisionRequest(
            prompt=request.prompt,
            images=request.images,
            conversation_context=request.conversation_context,
            task_type=context.task.value
        )

        log_structured(backend_log, "INFO", f"[MultiImageService] Invoking Gemini Vision provider for multi-image task '{context.task.value}'...")

        # 4. Perform multimodal cross-image reasoning via Gemini Vision
        raw_result = await self.provider.analyze(vision_req)

        # 5. Parse and normalize Gemini output into structured relationships & comparison models
        parsed_result: MultiImageResult = relationship_builder.parse_gemini_output(
            raw_text=raw_result.text,
            context=context,
            model_name=raw_result.model
        )

        # 6. Return unified VisionResult with structured metadata
        metadata = raw_result.metadata or {}
        metadata.update({
            "task_type": context.task.value,
            "ocr_used": parsed_result.ocr_used,
            "is_exact_duplicates": context.is_exact_duplicates,
            "duplicate_pairs": context.duplicate_pairs,
            "relationships": [rel.model_dump() for rel in parsed_result.relationships],
            "structured_comparison": parsed_result.structured_comparison.model_dump()
        })

        return VisionResult(
            text=parsed_result.text,
            provider=raw_result.provider,
            model=raw_result.model,
            image_count=len(request.images),
            task_type=context.task.value,
            visual_summary=parsed_result.visual_summary,
            uncertainty=raw_result.uncertainty,
            usage=raw_result.usage,
            metadata=metadata
        )

# Singleton Instance
multi_image_service = MultiImageService()

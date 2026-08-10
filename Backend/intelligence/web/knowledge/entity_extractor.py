"""
Deterministic Entity Extraction Engine for J.A.R.V.I.S. I2.2 V9.
"""
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from intelligence.web.knowledge.models import (
    EntityMention,
    EntityType,
    ProvenanceStatus,
    TemporalMetadata,
)
from intelligence.web.knowledge.entity_normalizer import entity_normalizer


class EntityExtractor:
    """
    Extracts entity mentions from prose, structured tables, JSON-LD, browser evidence,
    V3 research evidence, V4 temporal findings, V6 structured records, and V8 change findings.
    """

    KNOWN_ENTITY_PATTERNS = [
        # (pattern, EntityType)
        (r"\b(React|Vue|Angular|Svelte|Next\.js|Nuxt|Express|Django|FastAPI|Flask|Spring|Laravel)\b", EntityType.SOFTWARE),
        (r"\b(Python|JavaScript|TypeScript|Rust|Go|C\+\+|Java|Ruby|Swift|Kotlin|PHP)\b", EntityType.TECHNOLOGY),
        (r"\b(Meta|Google|Microsoft|Apple|Amazon|OpenAI|Anthropic|IBM|Oracle|NVIDIA|Tesla|Netflix|GitHub)\b", EntityType.COMPANY),
        (r"\b(United States|USA|UK|India|Germany|France|Japan|China|Canada|Australia)\b", EntityType.COUNTRY),
        (r"\b(New York|San Francisco|London|Tokyo|Berlin|Paris|Bengaluru|Sydney|Toronto)\b", EntityType.CITY),
    ]

    ORG_KEYWORDS = {"corp", "inc", "ltd", "llc", "company", "foundation", "lab", "labs", "technologies", "ai"}

    def extract_mentions_from_text(
        self,
        text: str,
        source_id: str,
        canonical_url: Optional[str] = None,
        source_path: Optional[str] = None,
        evidence_id: Optional[str] = None,
        temporal_metadata: Optional[TemporalMetadata] = None,
        provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED,
    ) -> List[EntityMention]:
        if not text or not text.strip():
            return []

        mentions: List[EntityMention] = []

        # 1. Regex pattern matches for high-confidence technology/software/company names
        for pattern, etype in self.KNOWN_ENTITY_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                surface = match.group(0).strip()
                norm = entity_normalizer.normalize(surface)
                if not norm:
                    continue

                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                ctx = text[start:end].replace("\n", " ").strip()

                mentions.append(
                    EntityMention(
                        mention_id=f"men_{uuid.uuid4().hex[:12]}",
                        surface_text=surface,
                        normalized_text=norm,
                        entity_type=etype,
                        source_id=source_id,
                        canonical_url=canonical_url,
                        source_path=source_path or "prose",
                        surrounding_context=ctx,
                        evidence_id=evidence_id,
                        temporal_metadata=temporal_metadata,
                        provenance_status=provenance_status,
                    )
                )

        # 2. Capitalized multi-word noun phrase extraction (e.g. "React Native", "OpenAI Research")
        cap_phrases = re.findall(r"\b[A-Z][a-zA-Z0-9\.\-']+(?:\s+[A-Z][a-zA-Z0-9\.\-']+)*\b", text)
        for phrase in cap_phrases:
            phrase_str = phrase.strip()
            if len(phrase_str) < 3 or phrase_str.lower() in ("the", "this", "that", "there", "these", "those", "http", "https"):
                continue

            # Check if already added
            norm = entity_normalizer.normalize(phrase_str)
            if any(m.normalized_text == norm for m in mentions):
                continue

            etype = self._classify_entity_type(phrase_str)
            mentions.append(
                EntityMention(
                    mention_id=f"men_{uuid.uuid4().hex[:12]}",
                    surface_text=phrase_str,
                    normalized_text=norm,
                    entity_type=etype,
                    source_id=source_id,
                    canonical_url=canonical_url,
                    source_path=source_path or "prose",
                    surrounding_context=phrase_str,
                    evidence_id=evidence_id,
                    temporal_metadata=temporal_metadata,
                    provenance_status=provenance_status,
                )
            )

        return mentions

    def extract_mentions_from_structured(
        self,
        structured_records: List[Dict[str, Any]],
        source_id: str,
        canonical_url: Optional[str] = None,
        provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED,
    ) -> List[EntityMention]:
        mentions: List[EntityMention] = []

        for idx, rec in enumerate(structured_records):
            rec_type = rec.get("record_type") or rec.get("@type") or "STRUCTURED_RECORD"
            rec_data = rec.get("record_data") or rec

            name = rec_data.get("name") or rec_data.get("title") or rec_data.get("label") or rec_data.get("entity_name")
            if isinstance(name, str) and name.strip():
                norm = entity_normalizer.normalize(name)
                etype = self._map_schema_type_to_entity_type(str(rec_type))
                mentions.append(
                    EntityMention(
                        mention_id=f"men_st_{uuid.uuid4().hex[:12]}",
                        surface_text=name.strip(),
                        normalized_text=norm,
                        entity_type=etype,
                        source_id=source_id,
                        canonical_url=canonical_url or rec_data.get("url"),
                        source_path=f"structured[{idx}].{rec_type}",
                        surrounding_context=str(rec_data)[:150],
                        evidence_id=rec.get("record_id") or rec.get("evidence_id"),
                        provenance_status=provenance_status,
                    )
                )

        return mentions

    def _classify_entity_type(self, text: str) -> EntityType:
        t_lower = text.lower()

        if any(w in t_lower for w in self.ORG_KEYWORDS):
            return EntityType.ORGANIZATION
        if "version" in t_lower or re.match(r"^v?\d+\.\d+", t_lower):
            return EntityType.VERSION
        if "app" in t_lower or "software" in t_lower or "framework" in t_lower or "library" in t_lower:
            return EntityType.SOFTWARE
        if "project" in t_lower:
            return EntityType.PROJECT
        if "dataset" in t_lower:
            return EntityType.DATASET
        if "standard" in t_lower or "spec" in t_lower or "rfc" in t_lower:
            return EntityType.STANDARD

        return EntityType.UNKNOWN

    def _map_schema_type_to_entity_type(self, schema_type: str) -> EntityType:
        st = schema_type.upper()
        if "ORGANIZATION" in st or "CORPORATION" in st:
            return EntityType.COMPANY
        if "PERSON" in st:
            return EntityType.PERSON
        if "SOFTWAREAPPLICATION" in st or "SOFTWARE" in st:
            return EntityType.SOFTWARE
        if "PRODUCT" in st:
            return EntityType.PRODUCT
        if "DATASET" in st:
            return EntityType.DATASET
        if "PLACE" in st or "CITY" in st or "COUNTRY" in st:
            return EntityType.PLACE
        if "EVENT" in st:
            return EntityType.EVENT

        return EntityType.UNKNOWN


entity_extractor = EntityExtractor()

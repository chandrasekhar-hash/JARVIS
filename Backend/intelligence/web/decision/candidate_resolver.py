"""
Candidate Entity Resolution Engine for J.A.R.V.I.S. I2.2 V11 Decision Intelligence.
"""
import re
import uuid
from typing import Dict, List, Optional, Any
from intelligence.web.decision.models import CandidateEntity


class CandidateResolver:
    """
    Composes V9 entity intelligence to extract and resolve unique candidate entities conservatively.
    Prevents duplicate candidate entities, same-name collisions, and version/product confusion.
    """

    def resolve_candidates_from_evidence(
        self, verified_evidence: List[Dict[str, Any]], query: str
    ) -> List[CandidateEntity]:
        candidates_by_name: Dict[str, CandidateEntity] = {}

        for ev in verified_evidence:
            text = ev.get("text", "")
            if not text:
                continue

            # Extract potential product/tech candidate names
            extracted_names = self._extract_candidate_names(text, query)
            for name in extracted_names:
                canonical = name.strip()
                norm_key = canonical.lower()

                if norm_key not in candidates_by_name:
                    # Parse attributes (price, ram, storage) from text if present
                    attrs = self._parse_attributes_from_text(name, text)
                    candidates_by_name[norm_key] = CandidateEntity(
                        candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
                        name=canonical,
                        canonical_name=canonical,
                        category="product" if any(w in query.lower() for w in ["laptop", "phone", "camera"]) else "technology",
                        attributes=attrs,
                    )
                else:
                    # Update attributes conservatively
                    existing = candidates_by_name[norm_key]
                    new_attrs = self._parse_attributes_from_text(name, text)
                    for k, v in new_attrs.items():
                        if v is not None and existing.attributes.get(k) is None:
                            existing.attributes[k] = v

        return list(candidates_by_name.values())

    def _extract_candidate_names(self, text: str, query: str) -> List[str]:
        names = []
        # Common comparison targets (e.g. React vs Vue, MacBook vs Dell XPS)
        matches = re.findall(r"\b([A-Z][a-zA-Z0-9_\-\.]{2,25}(?:\s+[A-Z0-9][a-zA-Z0-9_\-\.]{1,20}){0,3})\b", text)
        stop_words = {"The", "This", "That", "Here", "There", "Source", "Python", "Google", "Meta", "Microsoft", "Apple"}

        for m in matches:
            m_clean = m.strip()
            if m_clean not in stop_words and len(m_clean) > 3:
                names.append(m_clean)

        return list(set(names[:10]))

    def _parse_attributes_from_text(self, candidate_name: str, text: str) -> Dict[str, Any]:
        attrs = {}
        cand_lower = candidate_name.lower()
        t_lower = text.lower()

        if cand_lower in t_lower:
            # Parse price
            prices = re.findall(r"(?:₹|\$|usd|inr)\s*(\d+(?:,\d+)*(?:\.\d+)?)", text, re.IGNORECASE)
            if prices:
                attrs["price"] = float(prices[0].replace(",", ""))

            # Parse RAM
            rams = re.findall(r"(\d+)\s*gb\s*(?:ram|memory)?", text, re.IGNORECASE)
            if rams:
                attrs["ram"] = int(rams[0])

            # Parse storage
            storages = re.findall(r"(\d+)\s*(?:gb|tb)\s*(?:ssd|storage)", text, re.IGNORECASE)
            if storages:
                attrs["storage"] = int(storages[0])

        return attrs


candidate_resolver = CandidateResolver()

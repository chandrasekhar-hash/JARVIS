"""
J.A.R.V.I.S. Intelligence I2.2 V6 — JSON-LD & Schema.org Extractor.
Exclusively parses <script type="application/ld+json"> script blocks in HTML documents.
Supports single objects, arrays, and @graph structures. Treats metadata as evidence, not unverified truth.
"""
import json
import logging
from typing import List, Dict, Any, Union
from bs4 import BeautifulSoup

from intelligence.web.structured.models import (
    StructuredRecord,
    StructuredField,
    StructuredDataType,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_JSONLDExtractor")


class JSONLDExtractor:
    """
    Parses JSON-LD schema.org metadata embedded in HTML documents.
    """

    def extract_jsonld(
        self, html_content: str, source_id: str, canonical_url: str
    ) -> List[StructuredRecord]:
        records: List[StructuredRecord] = []
        if not html_content or 'type="application/ld+json"' not in html_content.lower() and "type='application/ld+json'" not in html_content.lower():
            return records

        soup = BeautifulSoup(html_content, "html.parser")
        scripts = soup.find_all("script", type=lambda t: t and "application/ld+json" in t.lower())

        for s_idx, script in enumerate(scripts):
            script_text = script.string or script.get_text()
            if not script_text or not script_text.strip():
                continue

            try:
                data = json.loads(script_text)
            except Exception as exc:
                logger.warning(f"Malformed JSON-LD script block {s_idx}: {exc}")
                continue

            # Process single object, array, or @graph
            entities = self._normalize_entities(data)
            for e_idx, (entity, entity_path) in enumerate(entities):
                if len(records) >= StructuredConfig.MAX_JSON_RECORDS:
                    break

                schema_type = entity.get("@type", "Thing")
                if isinstance(schema_type, list):
                    schema_type = "/".join(str(t) for t in schema_type)
                else:
                    schema_type = str(schema_type)

                fields: List[StructuredField] = []
                self._flatten_entity_properties(
                    entity, path=f"jsonld[{s_idx}].{entity_path}", fields=fields, depth=1
                )

                record_id = f"jsonld_{source_id}_{s_idx}_{e_idx}"
                record = StructuredRecord(
                    record_id=record_id,
                    record_type=StructuredDataType.JSON_LD,
                    fields=fields,
                    source_id=source_id,
                    canonical_url=canonical_url,
                    extraction_method="BS4_JSONLD",
                    schema_type=schema_type,
                )
                records.append(record)

        return records

    def _normalize_entities(self, data: Union[Dict, List]) -> List[tuple]:
        """
        Normalizes single object, array of objects, or @graph structure into list of (entity, entity_path).
        """
        entities = []
        if isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    entities.append((item, f"item[{idx}]"))
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                for idx, g_item in enumerate(data["@graph"]):
                    if isinstance(g_item, dict):
                        entities.append((g_item, f"@graph[{idx}]"))
            else:
                entities.append((data, "entity"))
        return entities

    def _flatten_entity_properties(
        self, obj: Any, path: str, fields: List[StructuredField], depth: int
    ):
        if depth > StructuredConfig.MAX_JSON_DEPTH:
            return

        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("@context",):
                    continue
                child_path = f"{path}.{k}"
                if isinstance(v, (dict, list)):
                    self._flatten_entity_properties(v, child_path, fields, depth + 1)
                else:
                    str_val = str(v)
                    if len(str_val) > StructuredConfig.MAX_JSON_STRING_LENGTH:
                        str_val = str_val[: StructuredConfig.MAX_JSON_STRING_LENGTH] + "...[TRUNCATED]"
                    fields.append(
                        StructuredField(
                            name=k,
                            value=str_val,
                            source_path=child_path,
                        )
                    )
        elif isinstance(obj, list):
            for idx, elem in enumerate(obj):
                elem_path = f"{path}[{idx}]"
                if isinstance(elem, (dict, list)):
                    self._flatten_entity_properties(elem, elem_path, fields, depth + 1)
                else:
                    str_val = str(elem)
                    if len(str_val) > StructuredConfig.MAX_JSON_STRING_LENGTH:
                        str_val = str_val[: StructuredConfig.MAX_JSON_STRING_LENGTH] + "...[TRUNCATED]"
                    fields.append(
                        StructuredField(
                            name=f"elem_{idx}",
                            value=str_val,
                            source_path=elem_path,
                        )
                    )


jsonld_extractor = JSONLDExtractor()

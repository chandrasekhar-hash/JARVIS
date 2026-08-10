"""
J.A.R.V.I.S. Intelligence I2.2 V6 — JSON Extractor.
Parses actual JSON bodies and responses, enforcing node traversal bounds, depth limits,
record limits, string length limits, hierarchy preservation, and deterministic source_paths.
"""
import json
import logging
from typing import List, Dict, Any, Tuple
from intelligence.web.structured.models import (
    StructuredRecord,
    StructuredField,
    StructuredDataset,
    StructuredDataType,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_JSONExtractor")


class JSONExtractor:
    """
    Parses JSON objects and arrays into structured datasets and records safely.
    Exclusively handles actual JSON bodies (not inline HTML script tags).
    """

    def extract_json(
        self, raw_json_str: str, source_id: str, canonical_url: str
    ) -> List[StructuredDataset]:
        datasets: List[StructuredDataset] = []
        if not raw_json_str or not raw_json_str.strip():
            return datasets

        try:
            parsed = json.loads(raw_json_str)
        except Exception as exc:
            logger.warning(f"Failed to parse JSON string: {exc}")
            return datasets

        visited_nodes = [0]
        records: List[StructuredRecord] = []
        is_truncated = False
        truncation_reason = None

        # Determine top-level array or object
        if isinstance(parsed, list):
            for idx, item in enumerate(parsed):
                if len(records) >= StructuredConfig.MAX_JSON_RECORDS:
                    is_truncated = True
                    truncation_reason = f"MAX_JSON_RECORDS limit ({StructuredConfig.MAX_JSON_RECORDS}) reached"
                    break

                fields, truncated_node = self._traverse_item(
                    item, path=f"json.items[{idx}]", depth=1, visited_nodes=visited_nodes
                )
                if truncated_node:
                    is_truncated = True
                    truncation_reason = "MAX_JSON_NODES or MAX_JSON_DEPTH limit reached"

                record = StructuredRecord(
                    record_id=f"json_{source_id}_rec_{idx}",
                    record_type=StructuredDataType.JSON,
                    fields=fields,
                    source_id=source_id,
                    canonical_url=canonical_url,
                    extraction_method="JSON_PARSER",
                )
                records.append(record)
        elif isinstance(parsed, dict):
            fields, truncated_node = self._traverse_item(
                parsed, path="json", depth=1, visited_nodes=visited_nodes
            )
            if truncated_node:
                is_truncated = True
                truncation_reason = "MAX_JSON_NODES or MAX_JSON_DEPTH limit reached"

            record = StructuredRecord(
                record_id=f"json_{source_id}_rec_0",
                record_type=StructuredDataType.JSON,
                fields=fields,
                source_id=source_id,
                canonical_url=canonical_url,
                extraction_method="JSON_PARSER",
            )
            records.append(record)

        if records:
            cols = [f.name for f in records[0].fields] if records else []
            dataset = StructuredDataset(
                dataset_id=f"json_ds_{source_id}",
                title="JSON Response Data",
                columns=cols,
                records=records,
                source_id=source_id,
                canonical_url=canonical_url,
                data_type=StructuredDataType.JSON,
                truncated=is_truncated,
                truncation_reason=truncation_reason,
                total_records_detected=len(records),
                records_returned=len(records),
            )
            datasets.append(dataset)

        return datasets

    def _traverse_item(
        self, obj: Any, path: str, depth: int, visited_nodes: List[int]
    ) -> Tuple[List[StructuredField], bool]:
        fields: List[StructuredField] = []
        node_truncated = False

        if visited_nodes[0] >= StructuredConfig.MAX_JSON_NODES:
            return fields, True

        if depth > StructuredConfig.MAX_JSON_DEPTH:
            return fields, True

        visited_nodes[0] += 1

        if isinstance(obj, dict):
            for k, v in obj.items():
                visited_nodes[0] += 1
                if visited_nodes[0] >= StructuredConfig.MAX_JSON_NODES:
                    node_truncated = True
                    break

                child_path = f"{path}.{k}"
                if isinstance(v, (dict, list)):
                    sub_fields, sub_trunc = self._traverse_item(v, child_path, depth + 1, visited_nodes)
                    fields.extend(sub_fields)
                    if sub_trunc:
                        node_truncated = True
                else:
                    str_val = str(v)
                    if len(str_val) > StructuredConfig.MAX_JSON_STRING_LENGTH:
                        str_val = str_val[: StructuredConfig.MAX_JSON_STRING_LENGTH] + "...[TRUNCATED]"
                        node_truncated = True

                    fields.append(
                        StructuredField(
                            name=k,
                            value=str_val,
                            source_path=child_path,
                        )
                    )
        elif isinstance(obj, list):
            for idx, elem in enumerate(obj):
                visited_nodes[0] += 1
                if visited_nodes[0] >= StructuredConfig.MAX_JSON_NODES:
                    node_truncated = True
                    break

                elem_path = f"{path}[{idx}]"
                if isinstance(elem, (dict, list)):
                    sub_fields, sub_trunc = self._traverse_item(elem, elem_path, depth + 1, visited_nodes)
                    fields.extend(sub_fields)
                    if sub_trunc:
                        node_truncated = True
                else:
                    str_val = str(elem)
                    if len(str_val) > StructuredConfig.MAX_JSON_STRING_LENGTH:
                        str_val = str_val[: StructuredConfig.MAX_JSON_STRING_LENGTH] + "...[TRUNCATED]"
                        node_truncated = True

                    fields.append(
                        StructuredField(
                            name=f"item_{idx}",
                            value=str_val,
                            source_path=elem_path,
                        )
                    )
        else:
            str_val = str(obj)
            if len(str_val) > StructuredConfig.MAX_JSON_STRING_LENGTH:
                str_val = str_val[: StructuredConfig.MAX_JSON_STRING_LENGTH] + "...[TRUNCATED]"
                node_truncated = True
            fields.append(
                StructuredField(
                    name="value",
                    value=str_val,
                    source_path=path,
                )
            )

        return fields, node_truncated


json_extractor = JSONExtractor()

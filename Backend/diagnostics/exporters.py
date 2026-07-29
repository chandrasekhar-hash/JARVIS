"""
Diagnostics Exporter System for J.A.R.V.I.S. Phase V1.8.
Supports Markdown, JSON, CSV formats, trace exports, and timeline event replays.
"""
import os
import csv
import json
import logging
from typing import Any, List, Dict, Optional

from .interfaces import IExporter
from .config import DiagnosticsConfig, diagnostics_config

logger = logging.getLogger("JARVIS_DiagnosticsExporter")


class DiagnosticsExporter(IExporter):
    """
    Exports diagnostic logs, traces, timelines, and health snapshots to JSON, Markdown, and CSV files.
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.config = config or diagnostics_config
        if not os.path.exists(self.config.export_directory):
            os.makedirs(self.config.export_directory, exist_ok=True)

    def export(self, data: Any, format_type: str = "json", destination: str = "") -> str:
        fmt = format_type.lower()
        filepath = destination or os.path.join(self.config.export_directory, f"export_{int(os.path.getmtime('.'))}.{fmt}")

        if fmt == "json":
            return self.export_json(data, filepath)
        elif fmt == "csv":
            return self.export_csv(data, filepath)
        elif fmt == "markdown" or fmt == "md":
            return self.export_markdown(str(data), filepath)
        else:
            raise ValueError(f"Unsupported export format '{format_type}'")

    def export_json(self, data: Any, filepath: str) -> str:
        try:
            dict_data = data.__dict__ if hasattr(data, "__dict__") else data
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(dict_data, f, indent=2, default=str)
            logger.info(f"[DiagnosticsExporter] Exported JSON to '{filepath}'.")
            return filepath
        except Exception as e:
            logger.error(f"[DiagnosticsExporter] Failed to export JSON: {e}")
            return ""

    def export_csv(self, data: List[Dict[str, Any]], filepath: str) -> str:
        if not data or not isinstance(data, list):
            return ""

        try:
            keys = list(data[0].keys())
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for row in data:
                    writer.writerow({k: str(v) for k, v in row.items()})
            logger.info(f"[DiagnosticsExporter] Exported CSV to '{filepath}'.")
            return filepath
        except Exception as e:
            logger.error(f"[DiagnosticsExporter] Failed to export CSV: {e}")
            return ""

    def export_markdown(self, markdown_text: str, filepath: str) -> str:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            logger.info(f"[DiagnosticsExporter] Exported Markdown to '{filepath}'.")
            return filepath
        except Exception as e:
            logger.error(f"[DiagnosticsExporter] Failed to export Markdown: {e}")
            return ""

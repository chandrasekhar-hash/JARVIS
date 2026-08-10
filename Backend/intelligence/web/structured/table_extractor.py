"""
J.A.R.V.I.S. Intelligence I2.2 V6 — HTML Table Extractor.
Uses DOM parsing (bs4) to extract structured tables, handling headers, rowspan, colspan,
captions, cell links, nested tables, and missing cells into logical 2D grids with reproducible source_paths.
"""
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

from intelligence.web.structured.models import (
    StructuredRecord,
    StructuredField,
    StructuredDataset,
    StructuredDataType,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_TableExtractor")


class TableExtractor:
    """
    Parses HTML tables into structured records and datasets using DOM matrix grid representation.
    """

    def extract_tables(
        self, html_content: str, source_id: str, canonical_url: str
    ) -> List[StructuredDataset]:
        datasets: List[StructuredDataset] = []
        if not html_content or "<table" not in html_content.lower():
            return datasets

        soup = BeautifulSoup(html_content, "html.parser")
        tables = soup.find_all("table")

        table_count = 0
        for table_idx, table in enumerate(tables):
            if table_count >= StructuredConfig.MAX_TABLES_PER_PAGE:
                break

            # Handle caption
            caption_tag = table.find("caption")
            caption_text = caption_tag.get_text(strip=True) if caption_tag else f"Table {table_idx + 1}"

            # Construct 2D grid mapping (row_idx, col_idx) -> cell_info
            grid, headers, malformed_rows, rows_parsed, is_truncated, truncation_reason = self._build_table_grid(table, table_idx)

            if not grid:
                continue

            table_count += 1
            dataset_id = f"table_{table_idx}_{source_id}"

            # Convert grid rows to StructuredRecords
            records: List[StructuredRecord] = []
            for r_idx, row in enumerate(grid):
                fields: List[StructuredField] = []
                row_is_malformed = malformed_rows.get(r_idx, False)

                for c_idx, cell_text in enumerate(row):
                    col_header = headers[c_idx] if c_idx < len(headers) else f"Column {c_idx + 1}"
                    source_path = f"table[{table_idx}].row[{r_idx}].cell[{c_idx}]"
                    fields.append(
                        StructuredField(
                            name=col_header,
                            value=cell_text,
                            source_path=source_path,
                            source_id=source_id,
                        )
                    )

                record_id = f"{dataset_id}_row_{r_idx}"
                records.append(
                    StructuredRecord(
                        record_id=record_id,
                        record_type=StructuredDataType.HTML_TABLE,
                        fields=fields,
                        source_id=source_id,
                        canonical_url=canonical_url,
                        extraction_method="BS4_DOM_GRID",
                        is_malformed=row_is_malformed,
                    )
                )

            dataset = StructuredDataset(
                dataset_id=dataset_id,
                title=caption_text,
                columns=headers,
                records=records,
                source_id=source_id,
                canonical_url=canonical_url,
                data_type=StructuredDataType.HTML_TABLE,
                truncated=is_truncated,
                truncation_reason=truncation_reason,
                total_records_detected=rows_parsed,
                records_returned=len(records),
            )
            datasets.append(dataset)

        return datasets

    def _build_table_grid(self, table: Tag, table_idx: int):
        """
        Builds a 2D matrix grid accounting for thead, tbody, tfoot, th, td, rowspan, and colspan.
        """
        grid: List[List[str]] = []
        headers: List[str] = []
        malformed_rows: Dict[int, bool] = {}

        # Find header cells from <thead> or first <tr> with <th>
        thead = table.find("thead")
        header_rows = thead.find_all("tr") if thead else []
        if not header_rows:
            # Fallback: check first tr in table
            first_tr = table.find("tr")
            if first_tr and first_tr.find_all("th"):
                header_rows = [first_tr]

        if header_rows:
            h_cells = header_rows[0].find_all(["th", "td"])
            for h_idx, h_cell in enumerate(h_cells):
                if h_idx >= StructuredConfig.MAX_TABLE_COLUMNS:
                    break
                text = h_cell.get_text(" ", strip=True)
                headers.append(text or f"Column {h_idx + 1}")

        # Extract body rows (excluding header rows if in thead)
        tbody = table.find("tbody")
        if tbody:
            body_rows = tbody.find_all("tr")
        else:
            all_trs = table.find_all("tr")
            if header_rows and all_trs and all_trs[0] == header_rows[0]:
                body_rows = all_trs[1:]
            else:
                body_rows = all_trs

        # Occupied matrix for rowspan/colspan tracking
        matrix: Dict[tuple, str] = {}
        max_cols = len(headers)
        current_row = 0
        is_truncated = False
        truncation_reason = None

        for tr in body_rows:
            if current_row >= StructuredConfig.MAX_TABLE_ROWS:
                is_truncated = True
                truncation_reason = f"MAX_TABLE_ROWS limit ({StructuredConfig.MAX_TABLE_ROWS}) reached"
                break

            current_col = 0
            cells = tr.find_all(["td", "th"])

            # Check if row cell count differs from header count
            if headers and len(cells) != len(headers):
                malformed_rows[current_row] = True

            for cell in cells:
                while (current_row, current_col) in matrix:
                    current_col += 1

                if current_col >= StructuredConfig.MAX_TABLE_COLUMNS:
                    break

                cell_text = cell.get_text(" ", strip=True)
                links = [a["href"] for a in cell.find_all("a", href=True)]
                if links:
                    cell_text += f" (links: {', '.join(links)})"

                rowspan = int(cell.get("rowspan", 1) or 1)
                colspan = int(cell.get("colspan", 1) or 1)
                rowspan = min(rowspan, 20)
                colspan = min(colspan, StructuredConfig.MAX_TABLE_COLUMNS)

                for r in range(rowspan):
                    for c in range(colspan):
                        target_row = current_row + r
                        target_col = current_col + c
                        if target_col < StructuredConfig.MAX_TABLE_COLUMNS:
                            matrix[(target_row, target_col)] = cell_text

                current_col += colspan
                if current_col > max_cols:
                    max_cols = min(current_col, StructuredConfig.MAX_TABLE_COLUMNS)

            current_row += 1

        # Convert matrix into grid rows
        total_rows = current_row
        for r in range(total_rows):
            row_data = []
            for c in range(max_cols):
                row_data.append(matrix.get((r, c), ""))
            grid.append(row_data)

        if not headers:
            headers = [f"Column {c + 1}" for c in range(max_cols)]

        return grid, headers, malformed_rows, total_rows, is_truncated, truncation_reason


table_extractor = TableExtractor()

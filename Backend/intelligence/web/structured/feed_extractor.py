"""
J.A.R.V.I.S. Intelligence I2.2 V6 — RSS & Atom Feed Extractor.
Parses RSS 2.0 and Atom feeds into structured records, integrating with V4 temporal semantics.
Missing dates explicitly set published_at = None. No manufactured timestamps.
"""
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from intelligence.web.structured.models import (
    StructuredRecord,
    StructuredField,
    StructuredDataset,
    StructuredDataType,
    StructuredConfig,
)

logger = logging.getLogger("JARVIS_FeedExtractor")


class FeedExtractor:
    """
    Extracts structured feed records from RSS 2.0 and Atom feeds using standard HTML/XML parser.
    """

    def extract_feed(
        self, feed_content: str, source_id: str, canonical_url: str
    ) -> List[StructuredDataset]:
        datasets: List[StructuredDataset] = []
        if not feed_content or not feed_content.strip():
            return datasets

        # Use html.parser which is built into python standard library
        soup = BeautifulSoup(feed_content, "html.parser")

        # 1. RSS 2.0 Parsing
        rss_items = soup.find_all("item")
        if rss_items:
            records = self._parse_rss_items(rss_items, source_id, canonical_url)
            dataset = StructuredDataset(
                dataset_id=f"rss_ds_{source_id}",
                title="RSS Feed Items",
                columns=["title", "link", "pubDate", "description", "guid", "author"],
                records=records,
                source_id=source_id,
                canonical_url=canonical_url,
                data_type=StructuredDataType.RSS,
                total_records_detected=len(rss_items),
                records_returned=len(records),
            )
            datasets.append(dataset)
            return datasets

        # 2. Atom Parsing
        atom_entries = soup.find_all("entry")
        if atom_entries:
            records = self._parse_atom_entries(atom_entries, source_id, canonical_url)
            dataset = StructuredDataset(
                dataset_id=f"atom_ds_{source_id}",
                title="Atom Feed Entries",
                columns=["title", "link", "published", "updated", "summary", "id", "author"],
                records=records,
                source_id=source_id,
                canonical_url=canonical_url,
                data_type=StructuredDataType.ATOM,
                total_records_detected=len(atom_entries),
                records_returned=len(records),
            )
            datasets.append(dataset)
            return datasets

        return datasets

    def _parse_rss_items(
        self, items: List[Any], source_id: str, canonical_url: str
    ) -> List[StructuredRecord]:
        records: List[StructuredRecord] = []
        for idx, item in enumerate(items):
            if idx >= StructuredConfig.MAX_FEED_ENTRIES:
                break

            fields: List[StructuredField] = []
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubdate") or item.find("pubDate")
            desc = item.find("description")
            guid = item.find("guid")
            author = item.find("author") or item.find("dc:creator")

            t_val = title.get_text(strip=True) if title else ""
            l_val = link.get_text(strip=True) if link else ""
            p_val = pub_date.get_text(strip=True) if pub_date else None
            d_val = desc.get_text(strip=True) if desc else ""
            g_val = guid.get_text(strip=True) if guid else ""
            a_val = author.get_text(strip=True) if author else ""

            fields.append(StructuredField(name="title", value=t_val, source_path=f"rss.channel.item[{idx}].title"))
            fields.append(StructuredField(name="link", value=l_val, source_path=f"rss.channel.item[{idx}].link"))
            fields.append(StructuredField(name="pubDate", value=p_val or "", source_path=f"rss.channel.item[{idx}].pubDate", normalized_value=p_val))
            fields.append(StructuredField(name="description", value=d_val[:1000], source_path=f"rss.channel.item[{idx}].description"))
            fields.append(StructuredField(name="guid", value=g_val, source_path=f"rss.channel.item[{idx}].guid"))
            fields.append(StructuredField(name="author", value=a_val, source_path=f"rss.channel.item[{idx}].author"))

            temporal_meta = {"published_at": p_val} if p_val else {"published_at": None}

            record = StructuredRecord(
                record_id=f"rss_{source_id}_{idx}",
                record_type=StructuredDataType.RSS,
                fields=fields,
                source_id=source_id,
                canonical_url=canonical_url,
                extraction_method="BS4_RSS",
                temporal_metadata=temporal_meta,
            )
            records.append(record)
        return records

    def _parse_atom_entries(
        self, entries: List[Any], source_id: str, canonical_url: str
    ) -> List[StructuredRecord]:
        records: List[StructuredRecord] = []
        for idx, entry in enumerate(entries):
            if idx >= StructuredConfig.MAX_FEED_ENTRIES:
                break

            fields: List[StructuredField] = []
            title = entry.find("title")
            link = entry.find("link")
            published = entry.find("published")
            updated = entry.find("updated")
            summary = entry.find("summary") or entry.find("content")
            e_id = entry.find("id")
            author = entry.find("author")

            t_val = title.get_text(strip=True) if title else ""
            l_val = link["href"] if link and link.has_attr("href") else (link.get_text(strip=True) if link else "")
            p_val = published.get_text(strip=True) if published else (updated.get_text(strip=True) if updated else None)
            u_val = updated.get_text(strip=True) if updated else None
            s_val = summary.get_text(strip=True) if summary else ""
            id_val = e_id.get_text(strip=True) if e_id else ""
            a_val = author.get_text(strip=True) if author else ""

            fields.append(StructuredField(name="title", value=t_val, source_path=f"atom.entry[{idx}].title"))
            fields.append(StructuredField(name="link", value=l_val, source_path=f"atom.entry[{idx}].link"))
            fields.append(StructuredField(name="published", value=p_val or "", source_path=f"atom.entry[{idx}].published", normalized_value=p_val))
            fields.append(StructuredField(name="updated", value=u_val or "", source_path=f"atom.entry[{idx}].updated", normalized_value=u_val))
            fields.append(StructuredField(name="summary", value=s_val[:1000], source_path=f"atom.entry[{idx}].summary"))
            fields.append(StructuredField(name="id", value=id_val, source_path=f"atom.entry[{idx}].id"))
            fields.append(StructuredField(name="author", value=a_val, source_path=f"atom.entry[{idx}].author"))

            temporal_meta = {"published_at": p_val, "updated_at": u_val} if p_val else {"published_at": None, "updated_at": u_val}

            record = StructuredRecord(
                record_id=f"atom_{source_id}_{idx}",
                record_type=StructuredDataType.ATOM,
                fields=fields,
                source_id=source_id,
                canonical_url=canonical_url,
                extraction_method="BS4_ATOM",
                temporal_metadata=temporal_meta,
            )
            records.append(record)
        return records


feed_extractor = FeedExtractor()

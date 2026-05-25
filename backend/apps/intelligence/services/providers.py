import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import requests

from apps.intelligence.models import RiskLevel, SanctionsSource, SourceCode, WatchlistEntry
from common.utils.countries import COUNTRY_ALIASES, COUNTRY_NAMES
from common.utils.strings import coalesce


class CountryCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data):
        if data.strip():
            self.chunks.append(data.strip())


class BaseProvider:
    timeout = 45

    def fetch(self, source: SanctionsSource) -> str:
        response = requests.get(
            source.endpoint,
            timeout=self.timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AMLCheckEnterprise/1.0; +https://localhost)",
                "Accept": "application/xml,text/xml,application/json,text/html;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8",
            },
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        raise NotImplementedError

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.split("}")[-1].upper()


class OFACProvider(BaseProvider):
    def parse(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        root = ET.fromstring(raw_text)
        entries = []
        for item in root.iter():
            if self._local_name(item.tag) != "SDNENTRY":
                continue
            data = {}
            aliases = []
            for child in item:
                name = self._local_name(child.tag)
                if name == "UID":
                    data["external_id"] = child.text or ""
                if name == "FIRSTNAME":
                    data["first_name"] = child.text or ""
                if name == "LASTNAME":
                    data["last_name"] = child.text or ""
                if name == "SDNTYPE":
                    data["entry_type"] = WatchlistEntry.EntryType.ENTITY if (child.text or "").upper() == "ENTITY" else WatchlistEntry.EntryType.PERSON
                if name == "AKALIST":
                    for aka in child:
                        alias_parts = []
                        for alias_field in aka:
                            if self._local_name(alias_field.tag) in {"FIRSTNAME", "LASTNAME", "WHOLE_NAME"}:
                                alias_parts.append(alias_field.text or "")
                        alias = " ".join(part for part in alias_parts if part).strip()
                        if alias:
                            aliases.append(alias)
            primary_name = coalesce(data.get("first_name"), data.get("last_name"))
            entries.append(
                {
                    "external_id": data.get("external_id", ""),
                    "entry_type": data.get("entry_type", WatchlistEntry.EntryType.PERSON),
                    "primary_name": primary_name or data.get("last_name", ""),
                    "aliases": aliases,
                    "raw_payload": data,
                }
            )
        return entries, []


class UNProvider(BaseProvider):
    def parse(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        root = ET.fromstring(raw_text)
        entries = []
        for node in root.iter():
            local_name = self._local_name(node.tag)
            if local_name not in {"INDIVIDUAL", "ENTITY"}:
                continue
            values = {}
            aliases = []
            countries = []
            for child in node:
                name = self._local_name(child.tag)
                if name in {"DATAID", "REFERENCE_NUMBER"}:
                    values["external_id"] = child.text or ""
                if name in {"FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME"}:
                    values.setdefault("name_parts", []).append(child.text or "")
                if name == "NATIONALITY" and list(child):
                    countries.extend(grand.text or "" for grand in child if grand.text)
                if name in {"INDIVIDUAL_ALIAS", "NAME_ORIGINAL_SCRIPT", "ALIAS_NAME"}:
                    alias_text = " ".join(grand.text or "" for grand in child if grand.text).strip()
                    if alias_text:
                        aliases.append(alias_text)
            entries.append(
                {
                    "external_id": values.get("external_id", ""),
                    "entry_type": WatchlistEntry.EntryType.PERSON if local_name == "INDIVIDUAL" else WatchlistEntry.EntryType.ENTITY,
                    "primary_name": " ".join(part for part in values.get("name_parts", []) if part).strip(),
                    "aliases": aliases,
                    "countries": countries,
                    "raw_payload": values,
                }
            )
        return entries, []


class EUProvider(BaseProvider):
    def parse(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        root = ET.fromstring(raw_text)
        entries = []
        for node in root.iter():
            if self._local_name(node.tag) != "SANCTIONENTITY":
                continue
            aliases = []
            countries = []
            external_id = ""
            entry_type = WatchlistEntry.EntryType.ENTITY
            for child in node:
                name = self._local_name(child.tag)
                if name in {"LOGICALID", "EUREFERENCE"}:
                    external_id = child.text or external_id
                if name == "SUBJECTTYPE":
                    entry_type = WatchlistEntry.EntryType.PERSON if "person" in (child.attrib.get("classificationCode", "").lower()) else WatchlistEntry.EntryType.ENTITY
                if name == "NAMEALIAS":
                    whole_name = child.attrib.get("wholeName", "")
                    if whole_name:
                        aliases.append(whole_name)
                if name == "CITIZENSHIP":
                    country = child.attrib.get("countryDescription", "")
                    if country:
                        countries.append(country)
            primary_name = aliases[0] if aliases else external_id
            entries.append(
                {
                    "external_id": external_id,
                    "entry_type": entry_type,
                    "primary_name": primary_name,
                    "aliases": aliases[1:] if len(aliases) > 1 else [],
                    "countries": countries,
                    "raw_payload": {"external_id": external_id},
                }
            )
        return entries, []


class FATFProvider(BaseProvider):
    BLACKLIST_HEADING = "High-Risk Jurisdictions subject to a Call for Action"
    GREYLIST_HEADING = "Jurisdictions under Increased Monitoring"

    def parse(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        parser = CountryCollector()
        parser.feed(raw_text)
        text = " ".join(parser.chunks)
        lower_text = text.lower()
        black_start = lower_text.find(self.BLACKLIST_HEADING.lower())
        grey_start = lower_text.find(self.GREYLIST_HEADING.lower())
        black_text = text[black_start:grey_start] if black_start >= 0 and grey_start > black_start else text
        grey_text = text[grey_start:] if grey_start >= 0 else text
        countries = []
        detection_terms = [(country, country) for country in COUNTRY_NAMES]
        detection_terms.extend((alias.title(), canonical) for alias, canonical in COUNTRY_ALIASES.items())
        for label, country in detection_terms:
            if label.lower() in black_text.lower() and country not in {item["country_name"] for item in countries}:
                countries.append(
                    {
                        "country_name": country,
                        "risk_level": RiskLevel.HIGH,
                        "list_name": "FATF Black List",
                        "notes": "High-Risk Jurisdictions subject to a Call for Action",
                    }
                )
        for label, country in detection_terms:
            if label.lower() in grey_text.lower() and country not in {item["country_name"] for item in countries}:
                countries.append(
                    {
                        "country_name": country,
                        "risk_level": RiskLevel.MEDIUM,
                        "list_name": "FATF Grey List",
                        "notes": "Jurisdictions under Increased Monitoring",
                    }
                )
        return [], countries


class InterpolProvider(BaseProvider):
    def parse(self, raw_text: str) -> tuple[list[dict], list[dict]]:
        payload = json.loads(raw_text)
        notices = payload.get("_embedded", {}).get("notices", []) or payload.get("notices", [])
        entries = []
        for notice in notices:
            primary_name = coalesce(notice.get("forename"), notice.get("name"))
            entries.append(
                {
                    "external_id": str(notice.get("entity_id") or notice.get("id") or ""),
                    "entry_type": WatchlistEntry.EntryType.PERSON,
                    "primary_name": primary_name,
                    "aliases": [],
                    "countries": [notice.get("nationality")] if notice.get("nationality") else [],
                    "nationality": notice.get("nationality", ""),
                    "source_url": notice.get("_links", {}).get("self", {}).get("href", ""),
                    "raw_payload": notice,
                }
            )
        return entries, []


PROVIDER_MAP = {
    SourceCode.OFAC: OFACProvider(),
    SourceCode.UN: UNProvider(),
    SourceCode.EU: EUProvider(),
    SourceCode.FATF: FATFProvider(),
    SourceCode.INTERPOL: InterpolProvider(),
}

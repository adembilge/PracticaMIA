"""Read identity fields from the official IPA Enti and Istat workbooks."""

from dataclasses import dataclass
from datetime import date
from io import BytesIO
import re

from openpyxl import load_workbook

PARSER_VERSION = "1"
IPA_LANDING = "https://indicepa.gov.it/ipa-dati/dataset/enti"
IPA_RESOURCE = (
    "https://indicepa.gov.it/ipa-dati/dataset/5baa3eb8-266e-455a-8de8-b1f434c279b2/"
    "resource/d09adf99-dc10-4349-8c53-27b1e5aa97b6/download/enti.xlsx"
)
ISTAT_LANDING = "https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/"
ISTAT_RESOURCE = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx"
SOURCES = {
    "ipa": ("AgID", "IPA Enti", IPA_LANDING, IPA_RESOURCE),
    "istat": ("Istat", "Elenco dei comuni italiani", ISTAT_LANDING, ISTAT_RESOURCE),
}
ISTAT_SHEET = re.compile(r"CODICI al (\d{2})_(\d{2})_(\d{4})", re.IGNORECASE)
ISTAT_AREA_CODE = "Codice dell'Unità territoriale sovracomunale (valida a fini statistici)"
ISTAT_AREA_NAME = "Denominazione dell'Unità territoriale sovracomunale (valida a fini statistici)"


@dataclass(frozen=True)
class DirectoryRow:
    kind: str
    code: str
    name: str
    parent_code: str | None = None
    alternative_name: str | None = None
    acronym: str | None = None
    area_type: str | None = None


def _text(value: object) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def _positions(headers: tuple, fields: tuple[str, ...]) -> dict[str, int]:
    cleaned = [_text(value) for value in headers]
    if any(cleaned.count(field) != 1 for field in fields):
        raise ValueError("Workbook must contain one of each required directory column")
    return {field: cleaned.index(field) for field in fields}


def _name(value: object) -> str:
    result = _text(value)
    if not result or len(result) > 1000:
        raise ValueError("Invalid directory name")
    return result


def _code(value: object, pattern: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError("Invalid external directory code")
    return value


def _add(entries: dict, row: DirectoryRow, *, repeated_parent: bool = False) -> None:
    key = row.kind, row.code
    if key in entries and (not repeated_parent or entries[key] != row):
        raise ValueError(f"Duplicate or inconsistent {row.kind} code {row.code}")
    entries[key] = row


def _parse_ipa(sheet) -> list[DirectoryRow]:
    rows = iter(sheet.values)
    positions = _positions(next(rows, ()), ("Codice_IPA", "Denominazione_ente", "Acronimo"))
    entries = {}
    for row in rows:
        if all(value is None for value in row):
            continue
        code = _code(row[positions["Codice_IPA"]], r"[A-Za-z0-9_-]{1,100}")
        _add(entries, DirectoryRow(
            "authority", code, _name(row[positions["Denominazione_ente"]]),
            acronym=_text(row[positions["Acronimo"]]) or None,
        ))
    return list(entries.values())


def _parse_istat(sheet) -> list[DirectoryRow]:
    rows = iter(sheet.values)
    fields = (
        "Codice Regione", "Denominazione Regione", ISTAT_AREA_CODE, ISTAT_AREA_NAME,
        "Tipologia di Unità territoriale sovracomunale", "Codice Comune formato alfanumerico",
        "Denominazione in italiano", "Denominazione altra lingua",
    )
    positions = _positions(next(rows, ()), fields)
    entries = {}
    for row in rows:
        if all(value is None for value in row):
            continue
        data = {field: row[position] for field, position in positions.items()}
        region = _code(data["Codice Regione"], r"[A-Z0-9]{2}")
        area = _code(data[ISTAT_AREA_CODE], r"[A-Z0-9]{3}")
        municipality = _code(data["Codice Comune formato alfanumerico"], r"[A-Z0-9]{6}")
        _add(entries, DirectoryRow(
            "region", region, _name(data["Denominazione Regione"]),
        ), repeated_parent=True)
        _add(entries, DirectoryRow(
            "province", area, _name(data[ISTAT_AREA_NAME]), parent_code=region,
            area_type=_name(data["Tipologia di Unità territoriale sovracomunale"]),
        ), repeated_parent=True)
        _add(entries, DirectoryRow(
            "municipality", municipality, _name(data["Denominazione in italiano"]),
            parent_code=area, alternative_name=_text(data["Denominazione altra lingua"]) or None,
        ))
    return list(entries.values())


def parse_workbook(provider: str, contents: bytes) -> tuple[date | None, list[DirectoryRow]]:
    if provider not in SOURCES:
        raise ValueError("Unknown official directory")
    workbook = load_workbook(BytesIO(contents), read_only=True, data_only=True, keep_links=False)
    try:
        if provider == "ipa":
            if len(workbook.worksheets) != 1:
                raise ValueError("Expected the single IPA Enti worksheet")
            reference_date, rows = None, _parse_ipa(workbook.worksheets[0])
        else:
            dated = [(sheet, ISTAT_SHEET.fullmatch(sheet.title)) for sheet in workbook.worksheets]
            matches = [(sheet, match) for sheet, match in dated if match]
            if len(matches) != 1:
                raise ValueError("Expected one dated Istat municipality worksheet")
            sheet, match = matches[0]
            day, month, year = map(int, match.groups())
            reference_date, rows = date(year, month, day), _parse_istat(sheet)
        if not rows:
            raise ValueError("The official directory is empty")
        return reference_date, rows
    finally:
        workbook.close()

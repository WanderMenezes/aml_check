import re
import unicodedata


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.upper()
    value = re.sub(r"[^A-Z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def coalesce(*values: str | None) -> str:
    return " ".join(str(value).strip() for value in values if value and str(value).strip())

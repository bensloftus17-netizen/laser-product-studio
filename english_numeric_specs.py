"""Conservative English-only handling for source-verified numerical specifications.

Never translate full foreign marketing claims automatically. Only translate a
small set of unambiguous labels paired with unchanged manufacturer numeric
values/units. Reject unsupported foreign technical fragments rather than
guess what they say. This is a deterministic source-labelled conversion, not
a new verified product specification or an AI-created claim.
"""
from __future__ import annotations

import re

# Labels are translated only when followed by a literal manufacturer numeric
# value with a recognised *unchanged* unit. Names and units are NOT inferred.
NUMERIC_LABELS = {
    "abmessungen": "Dimensions",
    "gewicht": "Weight",
    "länge": "Length",
    "breite": "Width",
    "höhe": "Height",
    "leistung": "Power",
    "spannung": "Voltage",
    "helligkeit": "Brightness",
    "akkukapazität": "Battery capacity",
    "ladezeit": "Charging time",
}
# English-only conversion for the precise, source-verified spanner-head sizes
# in part 9469. Do not translate free-form German selling claims.
INTERCHANGEABLE_HEADS_RE = re.compile(
    r"^\s*Auswechselbare\s+Schlüsselköpfe\s*:\s*"
    r"(?P<sizes>\d{1,3}(?:\s*,\s*\d{1,3})*(?:\s+und\s+\d{1,3})?)"
    r"\s*mm\.?\s*$", re.I,
)

LABEL_RE = re.compile(
    r"^\s*(?P<label>" + "|".join(re.escape(s) for s in NUMERIC_LABELS) +
    r")\s*:\s*(?P<value>\d[\d.,\s×xX/+%-]*\s*"
    r"(?:mm|cm|kg|g|W|V|mAh|Ah|lm|h|hrs?|hours?|min|minutes?)\s*)\.?\s*$",
    re.I,
)
RAW_GERMAN_TECH = re.compile(
    r"\b(?:abmessungen|gewicht|länge|breite|höhe|leistung|"
    r"spannung|helligkeit|akkukapazität|ladezeit|lieferumfang|"
    r"geschwindigkeitsstufen|leuchtdauer|akkulaufzeit|"
    r"betriebsdauer|drehzahl|arbeitsleuchte|betriebsanleitung|"
    r"einsatzbereich|anwendung|technische\s+daten|"
    r"schalter|beleuchtung|geschwindigkeit|schnellladung|"
    r"befestigung|werkstatt|schutzhülle|lichtstärke|"
    r"unbekannte|angaben|zubehör|werkstoff|beschreibung|"
    r"eigengewicht|gesamtgewicht|kabellänge|lichtleistung|"
    r"netzteil|mitgeliefert|lieferung|bedienungsanleitung|"
    r"anzahl|maße|farbtemperatur|geeignet|"
    r"auswechselbar\w*|wechselbar\w*|schlüsselköpfe|schluesselkoepfe|"
    r"maulschlüssel|schraubenschlüssel|steckschlüssel|schlüsselweite\w*|"
    r"schlüsselgröße\w*|aufsätze|spannweite|drehmomentschlüssel)\b",
    re.I,
)


def translate_known_numeric_labels(text):
    """Translate only exact German-labelled numerical facts, otherwise no-op.

    Supports a short compound fact such as the official 9476 technical line:
    'Abmessungen: 172 x 69 x 235 mm. Gewicht: 820 g.'
    -> 'Dimensions: 172 x 69 x 235 mm. Weight: 820 g.'
    A sentence with even one unknown foreign segment is *not* partially
    promoted as a translated manufacturer claim.
    """
    original=" ".join(str(text or "").split()).strip()
    if not original or not RAW_GERMAN_TECH.search(original):
        return original
    heads=INTERCHANGEABLE_HEADS_RE.fullmatch(original)
    if heads:
        # Preserve each official size and unit; translate only the heading
        # and the list conjunction ("und" -> "and").
        sizes=re.sub(r"\s+und\s+"," and ",heads.group("sizes"),flags=re.I)
        return f"Interchangeable spanner heads: {sizes} mm."
    # Split only between complete technical statements, not at decimal points.
    parts=re.split(r"(?<=\.)\s+(?=[A-Za-zÄÖÜäöüß])",original)
    if not parts:
        return original
    converted=[]
    for part in parts:
        m=LABEL_RE.fullmatch(part)
        if not m:
            return original
        label=NUMERIC_LABELS.get(m.group("label").casefold())
        if not label:
            return original
        value=m.group("value").strip()
        converted.append(f"{label}: {value}.")
    return " ".join(converted)


def normalise_numeric_spec_row(key,value):
    """Return translated (English label, unmodified value) or original row.

    Ambiguous claims are filtered by the calling product language checker.
    """
    name=" ".join(str(key or "").split())
    original=" ".join(str(value or "").split())
    joined=translate_known_numeric_labels(f"{name}: {original}")
    if joined != f"{name}: {original}" and joined.endswith("."):
        converted_key,converted_value=joined[:-1].split(": ",1)
        return converted_key,converted_value
    return name,original

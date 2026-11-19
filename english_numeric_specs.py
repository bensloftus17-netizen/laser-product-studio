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

# V62: The exact Dutch technical format found on the official Laser 7845
# source record. An independent English manufacturer page confirms the same
# 16 mm square section and 25° angled head:
# https://www.toolconnection.co.uk/products/general-hand-tools/striking-tools/pry-bars/heavy-duty/7845-pry-bar-900mm
# Never translate a broader Dutch sales claim or guess what its jargon means.
DUTCH_GEOMETRY_RE = re.compile(
    r"^\\s*vierkante\\s+doorsnede\\s+van\\s+"
    r"(?P<section>\\d{1,3}(?:[.,]\\d{1,2})?)\\s*mm\\s*[,;]\\s*"
    r"gebogen\\s+kop\\s+van\\s+"
    r"(?P<angle>\\d{1,3}(?:[.,]\\d{1,2})?)\\s*[°º]\\s*\\.?\\s*$",
    re.I,
)


def _translate_dutch_verified_geometry(text):
    match=DUTCH_GEOMETRY_RE.fullmatch(text)
    if not match:
        return None
    # The manufacturer-supplied numbers are never modified by translation.
    return (f'{match.group("section")} mm square section; '
            f'{match.group("angle")}° angled head.')


# V61: Strict English labels for verified *French numeric measurements*.
# A mixed/unsupported statement is not partially translated; its original
# foreign wording remains for the language gate to reject entirely.
FRENCH_NUMERIC_LABELS = {
    "longueur": "Length",
    "profondeur interne": "Internal depth",
    "profondeur": "Depth",
    "largeur": "Width",
    "hauteur": "Height",
    "diamètre": "Diameter",
    "épaisseur": "Thickness",
    "poids": "Weight",
}
FRENCH_NUMERIC_LABEL_RE = re.compile(
    r"^\s*(?P<label>" + "|".join(
        re.escape(k) for k in sorted(FRENCH_NUMERIC_LABELS,key=len,reverse=True)
    ) + r")\s*:\s*(?P<value>\d{1,5}(?:[.,]\d{1,3})?\s*"
    r"(?:mm|cm|kg|g|m))\s*\.?\s*$", re.I,
)
FRENCH_NUMERIC_MARKER = re.compile(
    r"\b(?:longueur|profondeur(?:\s+interne)?|largeur|hauteur|"
    r"diam[èe]tre|[ée]paisseur|poids)\s*:",re.I,
)


def _translate_french_numeric(text):
    """Convert exactly matched source measurements, retaining numbers/units.

    Example: 'Longueur : 120 mm, profondeur interne : 93 mm.'
    -> 'Length: 120 mm. Internal depth: 93 mm.'
    Other foreign claims are unchanged and subsequently rejected.
    """
    if not FRENCH_NUMERIC_MARKER.search(text):
        return None
    # Split only between a finished measurement and a new named label.
    pieces=re.split(
        r"\s*[,;]\s*(?=[A-Za-zÀ-ÿ][^,;:]{1,35}\s*:)",
        text.strip(),
    )
    rows=[]
    for piece in pieces:
        match=FRENCH_NUMERIC_LABEL_RE.fullmatch(piece)
        if not match:
            return None
        label=FRENCH_NUMERIC_LABELS[match.group("label").casefold()]
        rows.append(f'{label}: {match.group("value").strip()}.')
    return " ".join(rows) if rows else None


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
    if not original:
        return original
    dutch=_translate_dutch_verified_geometry(original)
    if dutch is not None:
        return dutch
    french=_translate_french_numeric(original)
    if french is not None:
        return french
    if not RAW_GERMAN_TECH.search(original):
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

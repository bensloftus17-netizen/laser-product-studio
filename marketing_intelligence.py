"""Laser Product Studio: transparent, source-grounded product-aware art direction.

This V19 classifier is deterministic, NOT a generative-AI integration.
Every marketing claim is sourced from the already-cleaned manufacturer record;
headline language is deliberately category-generic and never invents technical
specifications or comparisons. A future LLM may propose strategies, but must
produce the same validated schema and pass fact-checking before rendering.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Ordered specificity: a bearing kit mentioning use with a workshop press is a
# bearing kit, not a press; an impact wrench is not a general socket set.
PROFILES: dict[str, dict[str, Any]] = {
    "workshop_press": {
        "label": "Hydraulic & workshop presses",
        "style": "industrial_power",
        "angle": "Capacity, control and workshop capability",
        "headline": ("BUILT FOR", "WORKSHOP PRESSING."),
        "hero_focus": "Full-height equipment photograph; emphasise verified capacity",
        "priorities": ("tonne","ton ","capacity","air-hydraulic","hydraulic",
                       "pedal","foot control","working height","pressure","frame"),
        "spec_terms": ("capacity","tonnage","working","pressure","height","width","stroke"),
        "technical_preference": "dense",
        "accent": "#19A5E7",
    },
    "socket_ratchet": {
        "label": "Socket & ratchet sets",
        "style": "organised_kit",
        "angle": "Set contents, sizes, access and convenient storage",
        "headline": ("THE RIGHT KIT.", "READY TO WORK."),
        "hero_focus": "Complete, neatly framed genuine kit photograph",
        "priorities": ("piece","pc ","ratchet","drive","socket","size","tooth","teeth",
                       "set","case","tray","storage","chrome vanadium","steel"),
        "spec_terms": ("number of pieces","drive","number of teeth","length","storage",
                       "material","size","socket"),
        "technical_preference": "light",
        "accent": "#39A9F0",
    },
    "bearing_suspension": {
        "label": "Bearing & suspension tools",
        "style": "problem_solution",
        "angle": "Specific vehicle fitment and the workshop job the tool solves",
        "headline": ("MADE FOR", "THE RIGHT FIT."),
        "hero_focus": "Application-specific tool; show verified in-use photo if available",
        "priorities": ("application","sprinter","crafter","vehicle","bearing",
                       "hub","remov","fitting","install","press","sleeve","bush",
                       "clamshell","drive","strut","knuckle","separator"),
        "spec_terms": ("application","vehicle","dimension","size","length","diameter",
                       "number of pieces","drive"),
        "technical_preference": "dense",
        "accent": "#12A5DC",
    },
    "lighting_inspection": {
        "label": "Lighting & inspection",
        "style": "spotlight",
        "angle": "Visibility, brightness, access and run time",
        "headline": ("PUT THE JOB", "IN THE SPOTLIGHT."),
        "hero_focus": "Tall or compact lamp photo against subtle spotlight graphics",
        "priorities": ("lumens","brightness","cob","led","watt","magnetic","hook",
                       "hands-free","runtime","run time","battery","usb","recharge"),
        "spec_terms": ("lumens","power","battery","runtime","voltage","length","rating"),
        "technical_preference": "medium",
        "accent": "#58C8FA",
    },
    "air_power": {
        "label": "Air & power tools",
        "style": "performance",
        "angle": "Verified torque, drive size, performance and ergonomics",
        "headline": ("POWER FOR", "THE JOB."),
        "hero_focus": "Dynamic but accurate product packshot and performance callouts",
        "priorities": ("torque","nm","drive","air","impact","anvil","speed",
                       "weight","composite","noise","bar","psi","hammer"),
        "spec_terms": ("torque","drive","working pressure","speed","power",
                       "length","weight","air consumption"),
        "technical_preference": "medium",
        "accent": "#079FE3",
    },
    "diagnostic_electrical": {
        "label": "Diagnostic & electrical",
        "style": "precision_tech",
        "angle": "Verified functions, measurement ranges and usability",
        "headline": ("GET THE", "RIGHT READING."),
        "hero_focus": "Clear readable product photo and data-led graphic accents",
        "priorities": ("range","voltage","current","diagnos","test","measure",
                       "accuracy","display","battery","function","sensor"),
        "spec_terms": ("range","accuracy","voltage","current","power","display",
                       "measurement","battery"),
        "technical_preference": "medium",
        "accent": "#28B6DB",
    },
    "bodyshop_repair": {
        "label": "Bodyshop & repair",
        "style": "repair_workflow",
        "angle": "Repair application, process and supported materials",
        "headline": ("READY FOR", "REPAIR WORK."),
        "hero_focus": "Tool packshot with workshop repair-inspired graphic framing",
        "priorities": ("panel","dent","paint","body","repair","weld","pull",
                       "adhesive","plastic","bumper","application"),
        "spec_terms": ("capacity","dimension","size","material","application","weight"),
        "technical_preference": "medium",
        "accent": "#188CE0",
    },
    "workshop_service": {
        "label": "Workshop servicing",
        "style": "service_process",
        "angle": "Service task, capacity and practical use",
        "headline": ("WORKSHOP SERVICE.", "MADE SIMPLE."),
        "hero_focus": "Clear service-equipment image and confirmed functional details",
        "priorities": ("bleed","brake","capacity","litre","fluid","pressure","tank",
                       "reservoir","service","adapt","operation"),
        "spec_terms": ("capacity","pressure","reservoir","gauge","application","volume"),
        "technical_preference": "medium",
        "accent": "#0A8BCE",
    },
    "threading_cutting": {
        "label": "Threading & cutting tools",
        "style": "complete_set",
        "angle": "Included tools, supported sizes and neat kit organisation",
        "headline": ("TOOLS FOR", "THE PERFECT THREAD."),
        "hero_focus": "Organised full-set view with small data chips",
        "priorities": ("piece","tap","die","thread","size","holder","split",
                       "material","case","storage","cutting"),
        "spec_terms": ("number of pieces","size","diameter","material","storage"),
        "technical_preference": "light",
        "accent": "#389AD5",
    },
    "general_hand_tools": {
        "label": "General hand tools",
        "style": "workshop_essential",
        "angle": "Practical application, size, material and handling",
        "headline": ("BUILT FOR", "THE JOB IN HAND."),
        "hero_focus": "Large, clear genuine tool photograph",
        "priorities": ("drive","size","length","access","steel","grip",
                       "material","piece","function","use"),
        "spec_terms": ("drive","length","size","material","number of pieces"),
        "technical_preference": "light",
        "accent": "#1AA2E1",
    },
    "accessories_consumables": {
        "label": "Accessories & consumables",
        "style": "stockroom",
        "angle": "Supported sizes, quantity and practical application",
        "headline": ("THE RIGHT PART", "FOR THE TASK."),
        "hero_focus": "Clean item group photography and verified quantities",
        "priorities": ("pack","quantity","size","material","thread","compatible",
                       "length","diameter","application"),
        "spec_terms": ("quantity","pack","diameter","size","material","length"),
        "technical_preference": "light",
        "accent": "#1B92D4",
    },
}

# Title patterns only. Descriptions and feature lists can mention OTHER tools
# being used with the product, so may never override specific title matches.
TITLE_RULES = (
    ("workshop_press", r"\b(?:air[- ]hydraulic|hydraulic|workshop)\s+(?:workshop\s+)?press\b|\b\d{1,3}\s*(?:tonne|ton)\b.*\bpress\b"),
    ("workshop_service", r"\b(?:brake\s+bleed|bleeder|bleeding\s+kit|pressure\s+bleed|fluid\s+extractor)\b"),
    ("bearing_suspension", r"\b(?:wheel\s+bearing|bearing\s+(?:kit|tool|puller)|hub\s+(?:puller|spreader)|split\s+hub|knuckle|strut|ball\s+joint|suspension|bush(?:ing)?\s+(?:remov|install))"),
    ("air_power", r"\b(?:impact\s+wrench|air\s+(?:ratchet|drill|hammer|wrench)|pneumatic|electric\s+(?:drill|wrench)|power\s+tool)\b"),
    ("diagnostic_electrical", r"\b(?:diagnostic|scanner|multimeter|circuit\s+tester|voltage\s+tester|battery\s+tester|oscilloscope|endoscope|inspection\s+camera)\b"),
    ("lighting_inspection", r"\b(?:work\s+(?:light|lamp)|inspection\s+(?:light|lamp|torch)|under[\s-]*bonnet\s+(?:light|lamp)|torch|headlamp|floodlight)\b"),
    ("bodyshop_repair", r"\b(?:bodyshop|body\s+repair|dent|panel\s+(?:repair|beater)|paint\s+remov|plastic\s+repair|weld|bumper\s+repair)\b"),
    ("threading_cutting", r"\b(?:tap\s*(?:&|and)\s*die|thread\s+(?:repair|cutting)|tap\s+set|die\s+set|threading\s+set)\b"),
    ("socket_ratchet", r"\b(?:socket|ratchet|hex\s+bit\s+set|bit\s+set|torx\s+set|socketry)\b"),
    ("accessories_consumables", r"\b(?:consumable|spare\s+part|assortment|clips|washers|fasteners|gasket|nuts\s+&\s+bolts)\b"),
    ("general_hand_tools", r"\b(?:spanner|screwdriver|pliers|hammer|wrench|hex\s+key|punch|chisel|hand\s+tool|puller)\b"),
)

# Fallback only when a title contains no recognisable type.
DESCRIPTION_RULES = (
    ("workshop_service", r"\b(?:brake\s+bleeding\s+tool|fluid\s+extraction)\b"),
    ("bearing_suspension", r"\b(?:bearing\s+removal|suspension\s+strut)\b"),
    ("lighting_inspection", r"\b(?:rechargeable\s+lamp|cob\s+lamp)\b"),
    ("diagnostic_electrical", r"\b(?:diagnostic\s+testing|measure\s+voltage)\b"),
)

TECH_LABELS = {"light": "Product-focused", "medium": "Balanced technical", "dense": "Detailed technical"}
VALID_CATEGORIES = frozenset(PROFILES)


def detect_category(record: dict) -> tuple[str, str]:
    """Return (category, evidence source) from manufacturer-provided words."""
    title=str(record.get("title") or "").lower()
    # Drop leading part number. Avoid using long PDF data as title evidence.
    title=re.sub(r"^\s*[a-z]?\d{3,6}(?:[-\s:]+)", "", title).strip()
    for key,pattern in TITLE_RULES:
        if re.search(pattern,title,re.I):
            return key, "product title"
    desc=str(record.get("description") or "").lower()[:420]
    for key,pattern in DESCRIPTION_RULES:
        if re.search(pattern,desc,re.I):
            return key, "manufacturer description"
    return "general_hand_tools", "general workshop fallback"


def _feature_claims(record: dict) -> list[str]:
    values=[]
    for raw in record.get("features") or []:
        sentence=" ".join(str(raw).split()).strip(" •-")
        # No list of 50 measurements, unfinished fact or raw PDF paragraph.
        if not 12<=len(sentence)<=175 or sentence.endswith("…"):
            continue
        if sentence.lower() in {v.lower() for v in values}:
            continue
        values.append(sentence)
    return values


def rank_verified_features(record: dict, category: str | None = None, limit: int = 5) -> list[str]:
    """Rank real manufacturer facts only; never generate new claims."""
    key=category if category in PROFILES else detect_category(record)[0]
    priorities=PROFILES[key]["priorities"]
    features=_feature_claims(record)
    def score(item):
        idx,text=item
        low=text.lower()
        return (-sum((12-i) if token in low else 0 for i,token in enumerate(priorities)),
                len(text)>125,idx)
    return [v for _,v in sorted(enumerate(features),key=score)[:max(0,limit)]]


def rank_specs(record: dict, category: str | None = None, limit: int = 7) -> list[tuple[str, str]]:
    key=category if category in PROFILES else detect_category(record)[0]
    priority=PROFILES[key]["spec_terms"]
    entries=[(str(k).strip(),str(v).strip()) for k,v in (record.get("specs") or {}).items()
             if k and v and len(str(v))<=108]
    def score(item):
        idx,kv=item;label=kv[0].lower()
        pos=next((i for i,term in enumerate(priority) if term in label),99)
        return pos,idx
    return [kv for _,kv in sorted(enumerate(entries),key=score)[:max(0,limit)]]


def category_strategy(record: dict) -> dict[str, Any]:
    key,evidence=detect_category(record)
    p=PROFILES[key]
    points=rank_verified_features(record,key,5)
    selected=rank_specs(record,key,6)
    return {
        "category": key,
        "category_label": p["label"],
        "evidence": evidence,
        "marketing_angle": p["angle"],
        "headline": " ".join(p["headline"]),
        "headline_lines": list(p["headline"]),
        "visual_style": p["style"],
        "hero_focus": p["hero_focus"],
        "technical_preference": p["technical_preference"],
        "technical_label": TECH_LABELS[p["technical_preference"]],
        "accent": p["accent"],
        "selling_points": points[:3],
        "technical_priority": [{"label":k,"value":v} for k,v in selected[:5]],
        "needs_review": True,
        "method": "deterministic product-type and verified-fact rules (not a generative model)",
    }


def strategy_for(record: dict) -> dict[str, Any]:
    """Recompute to prevent clients claiming a category for another part."""
    return category_strategy(record)

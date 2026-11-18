"""Official Laser Tools website category tree and category-led marketing strategies.

Snapshot transcribed from https://www.toolconnection.co.uk/laser/products
(18 November 2026). These are *category names*, not part-number assignments.
A product is only marked website-verified when its authenticated, matching
Tool Connection product URL supplies the category path.

All branch/leaf categories inherit an explicitly named strategy. Product
features, price, vehicle fitment and suitability still come only from the
manufacturer's own individual product record.
"""
from __future__ import annotations

import re
import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, unquote

SOURCE_URL = "https://www.toolconnection.co.uk/laser/products"
SNAPSHOT_DATE = "2026-11-18"

# First two columns are official top level + department. Remaining semicolon
# separated entries are subcategories. Keep repeated labels in different
# departments separate. The website has more-specific levels on some product
# URLs (e.g. /wheel-bearings/gen2-wheel-bearing-kits/) than in its main menu.
TREE = """
50th Anniversary Range||
Hybrid/Electric Vehicles|Insulated Tools|Insulated Screwdrivers, Bits & Keys 1000v;Cutting;Pliers & Grips;Socketry;Spanners/Wrenches;Striking Tools;Torque Control;Trim & Pick-Up Tools
Hybrid/Electric Vehicles|EV Specialist Tools|
Hybrid/Electric Vehicles|High Voltage Tools & Testers|Testers & Accessories 1000v
Hybrid/Electric Vehicles|Hybrid & BEV Safety Packages|
Hybrid/Electric Vehicles|Hybrid Safety|Hybrid Signs;Rescue;Safety Barriers
Hybrid/Electric Vehicles|Personal Protection|Electrical Protection;Floor Protection;Hand Protection
Hybrid/Electric Vehicles|Storage|
Hybrid/Electric Vehicles|Vehicle Safety|High Voltage Protection;Safety Lockout;Safety Testing;Vehicle Signs & Labels
Hybrid/Electric Vehicles|Workshop Equipment|Fire Safety;Lifting
Hybrid/Electric Vehicles|Vehicle Charging|
Cars & Vans|Bodywork|Dent Removal;Door;Exterior Parts Removal;Glass Repair & Removal;Headlamp Tools;Interior Parts Removal;Mirror Tools;Panel Preparation;Panel Repair;PDC;Trim Tools;Washer Jet;Welding;Wiper Arm;Supports & Storage;Trim Clips & Fasteners;Rivets & Bolts;Bonnet Release;Pulling;Valetting;Plastics Repair;Aluminium Repair;Miracle System
Cars & Vans|Brakes|Brake Bleeding;Brake Caliper;Brake Disc & Drum;Brake Fluid;Brake Hose & Pipe;Brake Specialist
Cars & Vans|Electrical System|Alternator, Belts & Pulleys;Battery Tools & Testers;Removal Tools & Kits;Terminals & Connectors;Fuses;Auto Bulbs;Battery;Trim Clips & Fasteners
Cars & Vans|Engine|Air Conditioning;Cooling System;Cylinder Head & Valves;Diesel;Engine Block & Pistons;Exhaust;Fuel System;Oil Service;Petrol;Ignition
Cars & Vans|Engine Timing Tools|Alfa Romeo;Audi;BMW;Chrysler;Citroën;Fiat;Ford;Honda;Hyundai;Jaguar;Jeep;Lancia;Land Rover;Mazda;Mercedes-Benz;MINI;Nissan;Peugeot;Porsche;Renault;Rover;Timing Tools - Supplementary Tools;Toyota;Universal;Vauxhall/Opel;Volkswagen;Volvo;Stellantis Group;Chevrolet;Dacia;DS;Kia;Seat;Skoda;Suzuki;MG;Range Rover
Cars & Vans|Hybrid/Electric Vehicles|EV Specialist Tools;Hybrid & BEV Safety Packages;Vehicle Charging
Cars & Vans|MOT Testing|
Cars & Vans|Steering & Suspension|Coil Springs;General Ball Joints;Shock Absorbers;Steering;Suspension Bush;Universal Steering & Suspension Equipment;Wheel Hub Removal
Cars & Vans|Testing|Circuit Testers;Code Readers;Electrical;Inspection;Meters & Accessories
Cars & Vans|Transmission|Clutch & Flywheel;CV Joint & Drive Shaft;Gearbox & Differential;Hub Nut Removal;Wheel Bearings
Cars & Vans|Wheel & Tyre|Locking Wheel Nuts;Tyre Pressure;Tyre Tread;Tyre Valves;Tyre Workshop;Wheel Nut Sockets;Wheel Service
Cars & Vans|Workshop|Battery Tools & Testers
Cars & Vans|Towing|
Cars & Vans|Equipment|
Cars & Vans|Load Secure|
HGV & PSV|Transmission|Hub Removal;Clutch & Flywheel;Gearbox & Diff;Wheel Bearings
HGV & PSV|Bodywork|Trailer Repair;Trim Tools
HGV & PSV|Brakes|Brake Fluid & Hydraulics;Caliper;Disc & Drum
HGV & PSV|Engine|Cylinder Head & Valves;Diesel;Engine Block & Pistons;Exhaust;Oil Service;Cooling System
HGV & PSV|Steering & Suspension|Ball Joint;Steering;Workshop;Shock Absorbers
HGV & PSV|Testing|Circuit Testers
HGV & PSV|Wheel & Tyre|Service Tools;Tyre Removal & Fitting;Wheel Nuts
HGV & PSV|Electrical System|Terminals & Connectors;Battery;Auto Bulbs
Motorcycle|Brakes|Brake Bleeding;Brake Caliper;Brake Specialist
Motorcycle|Engine|Cylinder Head;Engine Block;Exhaust;Oil Service;Petrol
Motorcycle|Steering & Suspension|Coil Spring;Steering;Swinging Arm;Shock Absorbers
Motorcycle|Timing|Engine Locking;Pulley Removal & Fitting
Motorcycle|Transmission|Clutch & Flywheel
Motorcycle|Wheels & Tyres|Axles & Alignment;Tyre Fitting & Removal;Wheel Nut Sockets
Motorcycle|Workshop|Hand Tools;Lubrication
Motorcycle|Wheel & Tyre|Tyre Workshop
Bicycles|Accessories|
Bicycles|Axle/Hub|
Bicycles|Brakes|
Bicycles|Cassette/Freewheel|
Bicycles|Chain|
Bicycles|Crank/Bottom Bracket|
Bicycles|Frame/Fork|
Bicycles|General Hand Tools|
Bicycles|Headset|
Bicycles|Pedal|
Bicycles|Storage|
Bicycles|Wheel/Spoke|
General Hand Tools|Cutting & Drilling|Drill Bits;Hand Files;Saws;Scissors & Knives;Scrapers & Picks;Sharpening Tools;Thread Repair
General Hand Tools|Impact Socketry|Impact Socket Sets;Individual Sockets;Loose Sockets;Socket Accessories
General Hand Tools|Maintenance|Buildings;Inspection;Pipework;Riveting;Soldering;Wire Brushes
General Hand Tools|Measuring & Marking|Marking Tools;Measuring
General Hand Tools|Pliers & Grips|Circlip Pliers;Crimping Pliers;Engineers Pliers;Lock Grip Pliers;Snips & Cutters;Specialist Pliers;Wire Stripping;Clamps
General Hand Tools|Power Tool Accessories|Drill Abrasives;Drill Accessories;Quick Chuck System;Storage
General Hand Tools|Pullers & Extractors|Extractors;Pullers
General Hand Tools|Power Tools, Cordless|Cordless Grinder;Cordless Drill;Cordless Screwdriver;Cordless Impact Wrench;Cordless Polisher;Cordless Accessories
General Hand Tools|Screwdrivers, Bits & Keys|Automotive Bit Sets;Bit Drivers;Bit Drivers with Bits;Bits - Individual;General Bit Sets;Hex Keys;Hex Socket Bit Sets;Mortorq (MTS) Socket Bits;Ribe Socket Bit Sets;Screwdriver Sets;Screwdrivers;Spline Socket Bit Sets;Star Keys;Star Socket Bit Sets;Torx Plus Socket Bits;TS Star Socket Bits;PzDrive Socket Bit Sets
General Hand Tools|Socketry|Bit Drivers / Holders;General Ratchets;Individual Sockets;Individual Star Sockets;Other Socket Profiles;Socket Accessories;Socket Racks;Socket Sets;Specialist Ratchets;Star/Torx Socket Sets;Breaker Bars;Insulated Ratchets
General Hand Tools|Spanners/Wrenches|Adjustable Wrenches;Combination Spanner Sets;Combination Spanners;Crows Foot Wrench Sets;Crows Foot Wrenches;Flare Nut Wrench Sets;Flare Nut Wrenches;Heavy Duty Spanners;Open Jaw Spanner Sets;Open Jaw Spanners;Podgers;Ratchet Ring Spanner Sets;Ratchet Ring Spanners;Ring Spanner Sets;Ring Spanners;Socket / Box Spanners;Spanner Extensions;Star Spanners
General Hand Tools|Striking Tools|Hammers & Axes;Pry Bars;Punches & Chisels
General Hand Tools|Tools Storage|Chests & Cabinets;Carts & Tables;Magnetic Storage;Padlocks;Parts Trays;Pliers Storage;Screwdriver Storage;Socket Storage;Spanner Storage;Tool Bags;Toolboxes;Tool Kits;Tool Roll
General Hand Tools|Torque Control|Aluminium Torque Wrenches;Classic Torque Wrenches;Digital Torque;Economy Torque Wrenches;Insert Type Torque Wrenches;Micrometer Torque Wrenches;Specialist Torque Wrenches;Torque Adaptors/Gauges;Torque Multipliers;Torque Screwdrivers;Torque Testers;Insulated Torque Wrenches
Workshop|Air Tools & Accessories|Air Hammer Accessories;Air Hose;Air Tools
Workshop|Cleaning|Brushes/Buckets;Cleaning Equipment;Cloths & Sponges;Long Handled Brushes
Workshop|Engine|Exhaust
Workshop|Equipment|Access;Bench Equipment;Heat Induction;Lifting;Storage;Welding;Cutting;Heating;Hydraulic Press;Fire Safety;Cable Reels & Extension Leads;Dust Extraction;Vehicle Moving Accessories
Workshop|Fluid & Grease|ATF Transfer;Dispensers;Fluid Extractors;Fluid Transfer;Funnels;Grease Guns & Oil Cans;Hydraulic Pumps;Measuring Jugs;Oil/Fluid Drain;Drain Pumps;Anti-Seize
Workshop|Inspection - Lighting|Handlamps;Headlamps;Penlights;Torches;Workshop Lamps
Workshop|Office|Chairs;Clocks;Batteries - Disposable;Miscellaneous;Batteries - Rechargeable;Electrical
Workshop|Personal Protection|Floor Protection;Head & Skin Protection;Safety Lockout;Welding Protection;Working at Heights;Hand Protection
Workshop|Vehicle Protection|Bodywork Protection;Interior Protection;Seat Protection;Wing Protection;Safety Lockout
Workshop|Workwear & Safety Footwear|Footwear
Workshop|Abrasives & Cutting|Cleaning;Cutting;Grinding;Sanding;Accessories | Tools;Wire Wool / Brushes
Workshop|Adhesives, Sealers & Tapes|Tapes;Dispensers;Adhesives & Sealers
Workshop|Tools Storage|Consumables Storage;Tool Pouches
Workshop|General Fasteners|Bolts;Nuts;Washers;Screws;Pins & Clips;Bolts & Nuts;O-Ring;Wire-Lock;Seals
Workshop|Steering & Suspension|Steering
Workshop|Lifting & Jacking|Engine Support;Trolley Jacks;Air Jacks;Bottle Jacks;Farm Jacks;Axle Stands;Transmission Jacks;Car Ramps;Lifting & Jacking Pads;Lifting Tables;Vehicle Lifts
Consumables||
Assorted Boxes|Bodywork|Trim Clips & Fasteners;Rivets & Bolts;Welding
Assorted Boxes|Testing|Circuit Testers
Assorted Boxes|Brakes|Brake Hose & Pipe
Assorted Boxes|Air Tools & Accessories|Air Hose
Assorted Boxes|Electrical System|Auto Bulbs;Fuses;Terminals & Connectors;Trim Clips & Fasteners
Assorted Boxes|Engine|Cooling System;Exhaust;Fuel System;Oil Service
Assorted Boxes|Equipment|Welding
Assorted Boxes|Fluid & Grease|Grease Guns & Oil Cans
Assorted Boxes|General Fasteners|Screws;Nuts;Bolts;Washers;Pins & Clips;O-Ring
Assorted Boxes|Steering & Suspension|Steering
Assorted Boxes|Tools Storage|Tools Storage
Assorted Boxes|Transmission|Clutch & Flywheel
Spares||
New Products||
""".strip()

# Marketing lenses are recommendations only, never verified fitment or
# technical claims. Their reasons are derived from the type of category,
# not promises about actual conversion or customer demand.
LENSES = {
    "application_fitment": {
        "label": "Verified vehicle / engine application",
        "focus": "application", "channels": ("email", "website"),
        "audiences": ("Relevant specialist repair workshops", "Automotive tool distributors"),
        "reason": "Lead with manufacturer-confirmed vehicle or engine applications and the specific repair job.",
        "feature_terms": ("application", "vehicle", "engine", "compatible", "manufacturer", "fitment", "use on", "designed for"),
        "profile": "bearing_suspension",
    },
    "workshop_service": {
        "label": "Verified workshop procedure",
        "focus": "application", "channels": ("email", "social"),
        "audiences": ("Relevant vehicle repair workshops", "Automotive tool distributors"),
        "reason": "Explain the documented repair or servicing task, and use genuine product photographs.",
        "feature_terms": ("service", "removal", "installation", "repair", "brake", "wheel", "workshop", "application"),
        "profile": "workshop_service",
    },
    "kit_contents": {
        "label": "Kit contents and verified sizes",
        "focus": "benefit", "channels": ("social", "email"),
        "audiences": ("Independent automotive workshops", "Tool retailers and trade distributors"),
        "reason": "Show the exact pieces, drive sizes, materials and storage format stated by the manufacturer.",
        "feature_terms": ("piece", "include", "set", "socket", "ratchet", "size", "drive", "case", "contents", "storage"),
        "profile": "socket_ratchet",
    },
    "hand_tool_features": {
        "label": "Verified tool functionality",
        "focus": "benefit", "channels": ("social", "email"),
        "audiences": ("Independent automotive workshops", "Trade tool distributors"),
        "reason": "Feature the genuine tool photograph and documented gripping, access, drive or cutting specifications.",
        "feature_terms": ("size", "length", "grip", "pliers", "access", "cut", "handle", "drive", "material"),
        "profile": "general_hand_tools",
    },
    "measurement_specs": {
        "label": "Verified measuring range and tool specification",
        "focus": "benefit", "channels": ("website", "email"),
        "audiences": ("Workshop technical tool buyers", "Trade tool distributors"),
        "reason": "Prioritise documented dimensions, measuring range, resolution and intended use without inventing accuracy.",
        "feature_terms": ("range", "measurement", "measuring", "scale", "mm", "length", "graduat", "accuracy"),
        "profile": "general_hand_tools",
    },
    "cordless_power": {
        "label": "Verified powered-tool capability",
        "focus": "benefit", "channels": ("social", "email"),
        "audiences": ("Workshop power-tool buyers", "Trade tool distributors"),
        "reason": "Focus on manufacturer-confirmed drive, power requirements, tool function and included accessories.",
        "feature_terms": ("volt", "battery", "ah", "rpm", "torque", "speed", "includes", "power", "air"),
        "profile": "air_power",
    },
    "individual_drive_tools": {
        "label": "Verified drive sizes and tool function",
        "focus": "benefit", "channels": ("social", "website"),
        "audiences": ("Independent vehicle repair workshops", "Tool retailers and distributors"),
        "reason": "Show confirmed drive profile, sizes, ratchet mechanism and material, not unrelated set contents.",
        "feature_terms": ("drive", "size", "ratchet", "tooth", "teeth", "socket", "steel", "chrome", "length"),
        "profile": "socket_ratchet",
    },
    "equipment_specifications": {
        "label": "Verified equipment functions and operating specifications",
        "focus": "benefit", "channels": ("email", "website"),
        "audiences": ("Workshop equipment buyers", "Trade workshop suppliers"),
        "reason": "Show the documented function, power requirements, dimensions and intended workshop application.",
        "feature_terms": ("power", "voltage", "temperature", "watt", "capacity", "workshop", "operation", "size"),
        "profile": "workshop_service",
    },
    "torque_precision": {
        "label": "Torque range and verified precision",
        "focus": "benefit", "channels": ("email", "website"),
        "audiences": ("Repair workshops using torque-controlled tools", "Trade tool distributors"),
        "reason": "Prioritise confirmed range, drive, calibration information and use rather than unverified accuracy claims.",
        "feature_terms": ("torque", "nm", "range", "drive", "calibrat", "accuracy", "scale"),
        "profile": "general_hand_tools",
    },
    "capacity_equipment": {
        "label": "Verified equipment capacity",
        "focus": "benefit", "channels": ("email", "website"),
        "audiences": ("Workshop equipment buyers", "Professional vehicle repair workshops"),
        "reason": "Lead with manufacturer-published capacity, dimensions, configuration and relevant workshop use.",
        "feature_terms": ("capacity", "tonne", "ton ", "ram", "stroke", "lift", "hydraulic", "height", "width"),
        "profile": "workshop_press",
    },
    "electrical_testing": {
        "label": "Verified testing functions",
        "focus": "benefit", "channels": ("email", "linkedin"),
        "audiences": ("Automotive diagnostic and electrical specialists", "Trade tool distributors"),
        "reason": "Describe tested functions and published electrical specifications; avoid unsupported compatibility claims.",
        "feature_terms": ("diagnostic", "testing", "voltage", "current", "range", "reading", "circuit"),
        "profile": "diagnostic_electrical",
    },
    "ev_safety": {
        "label": "Verified HV and protection specifications",
        "focus": "application", "channels": ("email", "website"),
        "audiences": ("Qualified EV service professionals", "Specialist tool distributors"),
        "reason": "Present manufacturer-confirmed electrical ratings, standards and stated uses. Do not imply training or suitability.",
        "feature_terms": ("1000v", "volt", "insulated", "rated", "testing", "protection", "en ", "iec", "standard"),
        "profile": "diagnostic_electrical",
    },
    "bodyshop_application": {
        "label": "Documented body repair application",
        "focus": "application", "channels": ("social", "email"),
        "audiences": ("Vehicle body repair workshops", "Bodyshop supply distributors"),
        "reason": "Show the precise confirmed panel, trim, dent or repair application with genuine imagery.",
        "feature_terms": ("repair", "panel", "body", "trim", "dent", "remov", "weld", "application"),
        "profile": "bodyshop_repair",
    },
    "lighting_visibility": {
        "label": "Verified lighting and inspection specifications",
        "focus": "benefit", "channels": ("social", "email"),
        "audiences": ("Independent repair workshops", "Trade tool distributors"),
        "reason": "Prioritise published brightness, run-time, charging details and access features.",
        "feature_terms": ("lumen", "light", "lamp", "battery", "recharge", "run time", "inspection"),
        "profile": "lighting_inspection",
    },
    "fluids_service": {
        "label": "Documented fluid service and capacity",
        "focus": "application", "channels": ("email", "social"),
        "audiences": ("Vehicle servicing workshops", "Automotive workshop suppliers"),
        "reason": "Focus on confirmed vehicle-service operation, fluid compatibility and container capacity.",
        "feature_terms": ("fluid", "grease", "oil", "capacity", "litre", "transfer", "drain", "service"),
        "profile": "workshop_service",
    },
    "storage_organisation": {
        "label": "Confirmed storage capacity and organisation",
        "focus": "benefit", "channels": ("social", "website"),
        "audiences": ("Professional workshops", "Tool retailers"),
        "reason": "Show real storage layout, product dimensions and included accessories.",
        "feature_terms": ("storage", "drawer", "capacity", "case", "tray", "organis", "dimension"),
        "profile": "general_hand_tools",
    },
    "materials_consumables": {
        "label": "Verified sizes, materials and pack quantities",
        "focus": "benefit", "channels": ("website", "social"),
        "audiences": ("Automotive parts and consumables distributors", "Vehicle repair workshops"),
        "reason": "State documented material, quantity, dimensions and exact part specification; no unapproved discounts.",
        "feature_terms": ("quantity", "pack", "size", "material", "thread", "length", "diameter"),
        "profile": "accessories_consumables",
    },
    "ppe_specification": {
        "label": "Confirmed PPE standards and specifications",
        "focus": "benefit", "channels": ("website", "email"),
        "audiences": ("Workshop PPE purchasers", "Trade safety-equipment distributors"),
        "reason": "Use only published rating, material, size and standard. Do not promise protection beyond the source.",
        "feature_terms": ("standard", "rating", "certifi", "size", "material", "protection", "class"),
        "profile": "general_hand_tools",
    },
    "bicycle_maintenance": {
        "label": "Confirmed bicycle maintenance task",
        "focus": "application", "channels": ("social", "email"),
        "audiences": ("Cycle repair workshops", "Bicycle tool retailers"),
        "reason": "Show the documented cycle part, repair task and stated fitment only.",
        "feature_terms": ("bicycle", "chain", "cassette", "pedal", "crank", "headset", "wheel", "hub"),
        "profile": "workshop_service",
    },
    "motorcycle_service": {
        "label": "Confirmed motorcycle workshop application",
        "focus": "application", "channels": ("email", "social"),
        "audiences": ("Motorcycle repair workshops", "Motorcycle tool distributors"),
        "reason": "Explain the documented motorcycle system or maintenance task and applicable specifications.",
        "feature_terms": ("motorcycle", "application", "engine", "service", "brake", "clutch"),
        "profile": "workshop_service",
    },
    "product_awareness": {
        "label": "Verified product introduction",
        "focus": "benefit", "channels": ("social", "website"),
        "audiences": ("Relevant professional tool buyers", "Trade distributors"),
        "reason": "Lead with the real product photograph and the verified purpose, without fabricated benefits.",
        "feature_terms": ("includes", "size", "application", "feature", "design", "length"),
        "profile": "general_hand_tools",
    },
}
# Strategy hierarchy: exact department or leaf overrides beat broad top-level.
TOP_LENSES = {
    "50th Anniversary Range": "product_awareness",
    "Hybrid/Electric Vehicles": "ev_safety",
    "Cars & Vans": "workshop_service",
    "HGV & PSV": "workshop_service",
    "Motorcycle": "motorcycle_service",
    "Bicycles": "bicycle_maintenance",
    "General Hand Tools": "hand_tool_features",
    "Workshop": "workshop_service",
    "Consumables": "materials_consumables",
    "Assorted Boxes": "materials_consumables",
    "Spares": "materials_consumables",
    "New Products": "product_awareness",
}
GROUP_LENSES = {
    "Engine Timing Tools": "application_fitment",
    "Timing": "application_fitment",
    "Socketry": "kit_contents",
    "Impact Socketry": "kit_contents",
    "Screwdrivers, Bits & Keys": "hand_tool_features",
    "Pliers & Grips": "hand_tool_features",
    "Spanners/Wrenches": "hand_tool_features",
    "Torque Control": "torque_precision",
    "Measuring & Marking": "measurement_specs",
    "Power Tools, Cordless": "cordless_power",
    "Power Tool Accessories": "equipment_specifications",
    "Cutting & Drilling": "hand_tool_features",
    "Pullers & Extractors": "workshop_service",
    "Air Tools & Accessories": "cordless_power",
    "Steering & Suspension": "workshop_service",
    "Transmission": "workshop_service",
    "Brakes": "workshop_service",
    "Testing": "electrical_testing",
    "Electrical System": "electrical_testing",
    "High Voltage Tools & Testers": "ev_safety",
    "Insulated Tools": "ev_safety",
    "EV Specialist Tools": "ev_safety",
    "Hybrid & BEV Safety Packages": "ev_safety",
    "Hybrid Safety": "ev_safety",
    "Vehicle Safety": "ev_safety",
    "Personal Protection": "ppe_specification",
    "Bodywork": "bodyshop_application",
    "Inspection - Lighting": "lighting_visibility",
    "Fluid & Grease": "fluids_service",
    "Equipment": "equipment_specifications",
    "Lifting & Jacking": "capacity_equipment",
    "Workshop Equipment": "capacity_equipment",
    "Tools Storage": "storage_organisation",
    "Storage": "storage_organisation",
    "General Fasteners": "materials_consumables",
    "Workwear & Safety Footwear": "ppe_specification",
    "Vehicle Protection": "ppe_specification",
    "Adhesives, Sealers & Tapes": "materials_consumables",
    "Abrasives & Cutting": "materials_consumables",
    "Wheel & Tyre": "workshop_service",
    "Wheels & Tyres": "workshop_service",
    "Engine": "workshop_service",
}
LEAF_LENSES = {
    "Hydraulic Press": "capacity_equipment",
    "Bench Equipment": "equipment_specifications",
    "Heat Induction": "equipment_specifications",
    "Welding": "equipment_specifications",
    "Heating": "equipment_specifications",
    "Fire Safety": "ppe_specification",
    "Cable Reels & Extension Leads": "equipment_specifications",
    "Dust Extraction": "equipment_specifications",
    "Vehicle Moving Accessories": "capacity_equipment",
    "Engine Support": "capacity_equipment",
    "Lifting Tables": "capacity_equipment",
    "Vehicle Lifts": "capacity_equipment",
    "Workshop Press": "capacity_equipment",
    "Wheel Bearings": "application_fitment",
    "Wheel Hub Removal": "application_fitment",
    "Engine Locking": "application_fitment",
    "Timing Tools - Supplementary Tools": "application_fitment",
    "Socket Sets": "kit_contents",
    "General Ratchets": "individual_drive_tools",
    "Specialist Ratchets": "individual_drive_tools",
    "Individual Sockets": "individual_drive_tools",
    "Individual Star Sockets": "individual_drive_tools",
    "Loose Sockets": "individual_drive_tools",
    "Other Socket Profiles": "individual_drive_tools",
    "Socket Accessories": "individual_drive_tools",
    "Bit Drivers / Holders": "individual_drive_tools",
    "Socket Racks": "storage_organisation",
    "Breaker Bars": "individual_drive_tools",
    "Screwdriver Sets": "kit_contents",
    "Automotive Bit Sets": "kit_contents",
    "General Bit Sets": "kit_contents",
    "Hex Socket Bit Sets": "kit_contents",
    "Ribe Socket Bit Sets": "kit_contents",
    "Spline Socket Bit Sets": "kit_contents",
    "Star Socket Bit Sets": "kit_contents",
    "PzDrive Socket Bit Sets": "kit_contents",
    "Impact Socket Sets": "kit_contents",
    "Insulated Ratchets": "ev_safety",
    "Insulated Torque Wrenches": "ev_safety",
    "Battery Tools & Testers": "electrical_testing",
    "Code Readers": "electrical_testing",
    "Digital Torque": "torque_precision",
    "Torque Testers": "torque_precision",
    "Circuit Testers": "electrical_testing",
    "Safety Lockout": "ev_safety",
    "Vehicle Charging": "ev_safety",
    "Lifting": "capacity_equipment",
    "Trolley Jacks": "capacity_equipment",
    "Bottle Jacks": "capacity_equipment",
    "Axle Stands": "capacity_equipment",
    "Headlamps": "lighting_visibility",
    "Torches": "lighting_visibility",
}
# Manufacturer marques (Peugeot, BMW...) are a sub-category *of engine timing*
# and should inherit its fitment-led strategy, not generic publicity.
ROOT_ALIASES = {
    "hgv-psv": "HGV & PSV",
    "hybrid-electric-vehicles": "Hybrid/Electric Vehicles",
    "50th-anniversary-range": "50th Anniversary Range",
}
HOSTS = frozenset(("www.toolconnection.co.uk", "toolconnection.co.uk"))


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _build_tree():
    result = {}
    for raw in TREE.splitlines():
        if not raw.strip():
            continue
        root, group, leaves = (x.strip() for x in raw.split("|", 2))
        bucket = result.setdefault(root, {})
        if group:
            dest = bucket.setdefault(group, [])
            for leaf in (x.strip() for x in leaves.split(";") if x.strip()):
                if leaf not in dest:
                    dest.append(leaf)
    return result


TAXONOMY = _build_tree()


def marketing_for_path(path):
    """Assign a specific, explicit marketing lens to every known category."""
    if not path or path[0] not in TAXONOMY:
        return None
    top, group, leaf = (list(path) + ["", "", ""])[:3]
    lens = TOP_LENSES[top]
    if group in GROUP_LENSES:
        lens = GROUP_LENSES[group]
    if leaf in LEAF_LENSES:
        lens = LEAF_LENSES[leaf]
    # A marque-specific engine timing product must stay application-led.
    if group == "Engine Timing Tools" or (top == "Motorcycle" and group == "Timing"):
        lens = "application_fitment"
    # A vehicle-specific department must not be treated as general socketry.
    if top == "Hybrid/Electric Vehicles" and group == "Insulated Tools":
        lens = "ev_safety"
    item = LENSES[lens]
    profile = item["profile"]
    audiences = list(item["audiences"])
    if group == "Engine Timing Tools" or (top == "Motorcycle" and group == "Timing"):
        profile = "engine_timing"
        audiences = ["Engine repair and timing-belt workshops",
                     "Workshops specialising in relevant engine applications"]
    elif leaf in ("Wheel Bearings", "Wheel Hub Removal", "Hub Removal") or group == "Steering & Suspension":
        profile = "bearing_suspension"
        audiences = ["Bearing and suspension repair workshops",
                     "Automotive tool distributors"]
    return {"id": lens, **item, "profile": profile,
            "channels": list(item["channels"]),
            "audiences": audiences, "feature_terms": list(item["feature_terms"])}


def taxonomy_snapshot():
    """Public category directory; report honest number of indexed product URLs."""
    return {
        "source": SOURCE_URL, "snapshot_date": SNAPSHOT_DATE,
        "part_numbers_indexed": len(catalogue_part_index()),
        "index_is_complete": False,
        "top_category_count": len(TAXONOMY),
        "category_path_count": sum(
            1 + sum(1 + len(leaves) for leaves in groups.values())
            for groups in TAXONOMY.values()),
        "categories": [
            {
                "name": root, "marketing": marketing_for_path([root]),
                "departments": [
                    {"name": group, "marketing": marketing_for_path([root, group]),
                     "subcategories": [
                         {"name": leaf,
                          "marketing": marketing_for_path([root, group, leaf])}
                         for leaf in leaves
                     ]}
                    for group, leaves in groups.items()
                ],
            }
            for root, groups in TAXONOMY.items()
        ],
    }


def _match_name(segment, candidates) -> str | None:
    normal = slug(segment)
    return next((name for name in candidates if slug(name) == normal), None)


def category_from_product_url(url: str, part: str | None = None):
    """Map *one verified official product page* to the website hierarchy.

    No text similarity or AI guessing. The terminal URL segment must start
    with the exact part number. URLs from outside Tool Connection are ignored.
    """
    if not isinstance(url, str):
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() not in HOSTS:
        return None
    segments = [unquote(x).strip() for x in parsed.path.split("/") if x]
    if len(segments) < 3 or segments[0].casefold() != "products":
        return None
    filename = segments[-1]
    matched = re.fullmatch(r"(\d{3,6})(?:-(.*))?", filename, re.I)
    if not matched:
        return None
    sku = matched.group(1)
    if part is not None and sku.casefold() != str(part).strip().casefold():
        return None
    category_parts = segments[1:-1]
    top = _match_name(category_parts[0], TAXONOMY)
    if not top:
        return None
    path = [top]
    consumed = 1
    groups = TAXONOMY[top]
    if len(category_parts) >= 2 and groups:
        group = _match_name(category_parts[1], groups)
        if group:
            path.append(group)
            consumed += 1
            if len(category_parts) >= 3:
                leaf = _match_name(category_parts[2], groups[group])
                if leaf:
                    path.append(leaf)
                    consumed += 1
        else:
            # This branch may be a newer department absent from the snapshot.
            # Preserve it but explicitly label it as a product-URL-only path.
            pass
    # Never discard a legitimate extra level in the official URL.
    extras = category_parts[consumed:]
    path.extend(extras_to_label(x) for x in extras)
    base_depth = len(category_parts) - len(extras)
    known_depth = consumed
    strategy = marketing_for_path(path[:known_depth])
    if not strategy:
        return None
    # Extra levels are provided in the manufacturer's URL, not in our menu
    # snapshot. The source is still official, but the snapshot match is partial.
    status = "verified_official_url" if not extras else "verified_official_url_extra_levels"
    return {
        "part": sku,
        "path": path,
        "breadcrumb": " › ".join(path),
        "top_category": path[0],
        "department": path[1] if len(path) > 1 else None,
        "subcategory": path[2] if len(path) > 2 else None,
        "manufacturer_url": url,
        "source": status,
        "taxonomy_snapshot_match_depth": known_depth,
        "marketing": strategy,
    }


def extras_to_label(raw: str) -> str:
    """Keep manufacturer URL meaning, don't claim a verified site menu label."""
    return str(raw).replace("-", " ").strip().title()


def apply_official_taxonomy(record: dict):
    """Return augmented copy. Never claim a category when source is not exact."""
    if not isinstance(record, dict):
        return record
    part = record.get("part")
    url = record.get("source")
    category = category_from_product_url(url, part)
    if category:
        return {**record, "official_taxonomy": category}
    return record


def select_marketing_fact(record, verified_facts, marketing):
    """Choose an exact approved fact relevant to the category's strategy.

    A matching word in a real manufacturer fact may prioritise that fact,
    but never lets the AI compose, enhance or paraphrase a technical claim.
    """
    if not verified_facts:
        return ""
    terms = marketing.get("feature_terms") or ()
    candidates = list(verified_facts)
    scored = [
        (sum((len(terms)-index) if term.lower() in fact.lower() else 0
             for index, term in enumerate(terms)),
         -index, fact)
        for index, fact in enumerate(candidates)
    ]
    return max(scored)[2]

INDEX_FILE = Path(__file__).resolve().parent / "data" / "catalogue_index.json"


@lru_cache(maxsize=1)
def catalogue_part_index():
    """Read checked example URLs or an imported company product-URL export.

    Only a URL that passes the exact part-number and Tool Connection host
    checks is eligible. An index entry is *not* itself proof of live product
    page availability; the existing lookup still retrieves the source.
    """
    try:
        source = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    entries = source.get("products", {}) if isinstance(source, dict) else {}
    if not isinstance(entries, dict):
        return {}
    return {
        str(part): url
        for part, url in entries.items()
        if isinstance(url, str) and category_from_product_url(url, str(part))
    }


def catalogue_url_for_part(part: str):
    return catalogue_part_index().get(str(part).strip())

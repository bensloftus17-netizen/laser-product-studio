"""Audited manufacturer catalogue leads for unreliable keyless search (V74).

Every entry was individually researched from an official, public product page
on 23 Nov 2026. These are bounded, dated discovery snapshots, not live
retailer offers or proof of stock, price, fitment, availability or relative
superiority. Live product page data overrides a snapshot whenever available.

The catalogue is structured by *tool family*, never by Laser part number;
new product categories can be added without changing the comparison engine.
"""
from __future__ import annotations
from copy import deepcopy

CHECKED_DATE = "2026-11-23"
REFERENCES = {
    "magnetic toolbox storage set": [{
        "brand": "FIRST4MAGNETS",
        "sku": "F4MTBHK",
        "title": "FIRST4MAGNETS 4 Piece Magnetic Toolbox Holder Kit",
        "url": "https://www.first4magnets.com/product/4-piece-magnetic-toolbox-holder-kit-121704",
        "verified_specs": {"Number of pieces": "4",
                           "Kit contents": '6" shelf, 12" shelf, spray can holder and paper towel holder'},
        "relationship": "Four-piece magnetic toolbox storage alternative with different kit contents",
        "source_checked_on": "2026-11-26",
    }],
    "insulated key set": [
        {
            "brand":"Sealey", "sku":"AK7177",
            "title":"Sealey Premier Extra-Long Hex Key Set 6pc - VDE Approved",
            "url":"https://www.sealey.co.uk/premier-extra-long-hex-key-set-6pc-vde-approved-ak7177/",
            "verified_specs":{"Number of pieces":"6","Profile":"Hex"},
            "relationship":"Hex-profile alternative; compare key sizes and profiles",
            "source_checked_on":"2026-11-26",
        },
        {
            "brand":"Sealey", "sku":"AK7178",
            "title":"Sealey Premier Extra-Long TRX-Star Key Set 9pc - VDE Approved",
            "url":"https://www.sealey.co.uk/premier-extra-long-trx-star-key-set-9pc-vde-approved-ak7178/",
            "verified_specs":{"Number of pieces":"9","Profile":"TRX-Star"},
            "relationship":"Star-profile alternative; compare key sizes and profiles",
            "source_checked_on":"2026-11-26",
        },
    ],
    "hub nut socket set": [{
        "brand": "Sealey",
        "sku": "SX053",
        "title": "Sealey Impact Hub Socket & Socket Bit Set, 1/2 in Drive, 12-Point, 5pc",
        "url": "https://www.sealey.co.uk/impact-hub-socket-socket-bit-set-1-2-sq-drive-12-point-5pc-sx053/",
        "verified_specs": {"Drive": "1/2 in", "Number of pieces": "5", "Profile": "12-point"},
        "relationship": "Related five-piece hub socket set; compare bit coverage and vehicle applications",
        "source_checked_on": "2026-11-25",
    }],
    # Independently checked official manufacturer pages, 23 Nov 2026.
    # These international sources establish competing pneumatic scraper
    # products, NOT UK stock, prices or interchangeable accessories.
    "pneumatic gasket scraper": [
        {
            "brand": "Astro Pneumatic",
            "sku": "1750K",
            "title": "Astro Pneumatic Air Scraper Kit - Includes 4 Specialty Blades (1750K)",
            "url": "https://www.astrotools.com/product/air-scraper-kit-includes-4-specialty-blades/",
            "verified_specs": {
                "Included blades": "4 specialty blades",
                "Air consumption": "3 CFM",
                "Maximum air pressure": "90 psi",
                "Sound level": "93 dB(A)",
                "Vibration": "9 m/s²",
                "Air inlet": "1/4 in",
            },
            "method": "Pneumatic scraper kit",
            "relationship": "Related air-powered gasket/paint scraper; verify blade fit and use",
            "source_checked_on": CHECKED_DATE,
        },
        {
            "brand": "Beswell",
            "sku": "BW-CH06",
            "title": "Beswell Straight Air Gasket Scraper (BW-CH06)",
            "url": "https://beswellpowertools.com/products/straight-air-gasket-scraper",
            "verified_specs": {
                "Blows per minute": "4000",
                "Operating pressure": "90 psi",
                "Air inlet": "1/4 in",
                "Tool length": "248 mm",
                "Tool weight": "0.7 kg",
            },
            "method": "Pneumatic straight gasket scraper",
            "relationship": "Related air-powered gasket scraper; accessories and application unverified",
            "source_checked_on": CHECKED_DATE,
        },
    ],
    "brake bleeder": [
        {
            "brand": "Draper",
            "sku": "22495",
            "title": "Draper Manual Pressure Brake Bleeder 2L (22495)",
            "url": "https://www.drapertools.com/product/22495/pump-action-brake-bleeder/",
            "verified_specs": {
                "Fluid capacity": "2 L",
                "Operating pressure": "10 psi",
                "Maximum pressure": "30 psi",
                "Gauge range": "0–70 psi",
            },
            "method": "manual hand-pump pressure bleeder",
            "relationship": "Close manual 2L alternative",
            "source_checked_on": CHECKED_DATE,
        },
        {
            "brand": "Hilka",
            "sku": "12724211",
            "title": "Hilka 2L Manual Pressure Brake Bleeder (12724211)",
            "url": "https://hilka.co.uk/2l-manual-pressure-brake-bleeder-12724211.html",
            "verified_specs": {
                "Fluid capacity": "2 L",
                "Operating pressure": "10 psi",
                "Maximum pressure": "30 psi",
                "Adaptor neck": "44 mm",
            },
            "method": "manual hand-pump pressure bleeder",
            "relationship": "Close manual 2L alternative",
            "source_checked_on": CHECKED_DATE,
        },
        {
            "brand": "Sealey",
            "sku": "VS820",
            "title": "Sealey Brake & Clutch Bleeding System 2.5L (VS820)",
            "url": "https://www.sealey.co.uk/brake-clutch-bleeding-system-2-5l-vs820/",
            "verified_specs": {
                "Fluid capacity": "2.5 L",
                "Maximum pressure": "30 psi",
                "Adaptor neck": "45 mm",
            },
            "method": "manual hand-pump pressure bleeder",
            "relationship": "Related manual pressure system (2.5L)",
            "source_checked_on": CHECKED_DATE,
        },
        {
            "brand": "Draper",
            "sku": "29358",
            "title": "Draper Clutch and Brake Bleeding Kit 3L (29358)",
            "url": "https://www.drapertools.com/product/29358/clutch-and-brake-bleeding-kit/",
            "verified_specs": {
                "Fluid capacity": "3 L",
                "Maximum pressure": "80 psi",
                "Waste oil capacity": "1 L",
            },
            "method": "manual hand-pump pressure bleeder",
            "relationship": "Related manual pressure system (3L)",
            "source_checked_on": CHECKED_DATE,
        },
    ],
}


def catalogue_references(tool_type):
    """Give defensive copies of verified manufacturer search pointers."""
    return deepcopy(REFERENCES.get(str(tool_type or ""), []))

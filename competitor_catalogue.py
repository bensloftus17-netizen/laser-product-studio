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

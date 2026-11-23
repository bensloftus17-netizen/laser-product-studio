"""V79: product-specific but category-driven competitor discovery for Laser 9517.

Source links were checked on the official Astro Pneumatic/Beswell pages
23 November 2026. These are NOT UK RRP, stock, exact replacement or
performance-superiority claims. Tests do not make external requests.
"""
import unittest
from unittest.mock import patch

from competitor_catalogue import catalogue_references
from competitor_finder import (
    tool_signature,match_status,keyless_discovery,research_competitors,
)

LASER_9517={
    "part":"9517",
    "title":"Multi-Blade Pneumatic Scraper Kit",
    "features":["Five-piece blade set for scraping gaskets."],
    "specs":{"Working pressure":"90 psi"},
    "source":"https://lasertools.toolconnection.co.uk/product/9517/Multi-Blade-Pneumatic-Scraper-Kit",
}


class PneumaticGasketScraperV79Tests(unittest.TestCase):
    def test_9517_tool_family_detected_from_official_name(self):
        signature=tool_signature(LASER_9517)
        self.assertEqual(signature["type"],"pneumatic gasket scraper")
        self.assertEqual(signature["category_source"],"fixed-category-rule")

    def test_9517_matches_air_powered_competitors_not_hand_scrapers(self):
        signature=tool_signature(LASER_9517)
        self.assertTrue(match_status(signature,
            "Astro Pneumatic Air Scraper Kit - Includes 4 Specialty Blades"))
        self.assertTrue(match_status(signature,
            "Beswell Straight Air Gasket Scraper"))
        self.assertIsNone(match_status(signature,"Sealey Hand Gasket Scraper"))
        self.assertIsNone(match_status(signature,"Draper Manual Gasket Scraper"))

    def test_no_shopping_provider_returns_two_dated_source_links(self):
        with patch("competitor_finder._get_product_page",return_value=None),\
             patch("competitor_finder.rss_search",side_effect=AssertionError("Unneeded RSS")):
            report=research_competitors(
                LASER_9517,shopping_key="",enable_ai=False)
        self.assertEqual(report["laser"]["part"],"9517")
        self.assertEqual(report["laser"]["tool_type"],"pneumatic gasket scraper")
        self.assertGreaterEqual(report["count"],2,report)
        by_brand={row["brand"]:row for row in report["results"]}
        for brand in ("Astro Pneumatic","Beswell"):
            item=by_brand[brand]
            self.assertTrue(item["product_url"].startswith("https://"))
            self.assertEqual(item["source_type"],"manufacturer catalogue reference")
            self.assertIsNone(item["price_gbp"])
            self.assertIsNone(item["image_url"])
            self.assertEqual(item["source_checked_on"],"2026-11-23")
        self.assertTrue(report["review_required"])

    def test_published_source_specs_not_unverified_pricing(self):
        records=catalogue_references("pneumatic gasket scraper")
        self.assertEqual(len(records),2)
        by_brand={item["brand"]:item for item in records}
        self.assertEqual(by_brand["Astro Pneumatic"]["verified_specs"]["Air consumption"],
                         "3 CFM")
        self.assertEqual(by_brand["Beswell"]["verified_specs"]["Operating pressure"],
                         "90 psi")
        self.assertTrue(all("price" not in item for item in records))
        self.assertTrue(all(item["source_checked_on"]=="2026-11-23"
                            for item in records))


if __name__=="__main__":
    unittest.main()

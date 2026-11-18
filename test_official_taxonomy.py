"""Official Laser category tree, exact-SKU URLs and marketing-rule audit tests."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as studio
from campaign_strategy import explain_strategy, strategy_options
from import_catalogue import import_catalogue_csv
from marketing_intelligence import detect_category, strategy_for
from official_taxonomy import (
    LENSES, TAXONOMY, SOURCE_URL, SNAPSHOT_DATE,
    category_from_product_url, catalogue_part_index, catalogue_url_for_part,
    apply_official_taxonomy, marketing_for_path, taxonomy_snapshot,
)


class OfficialTaxonomyTests(unittest.TestCase):
    def test_full_site_menu_has_per_subcategory_marketing_lens(self):
        snapshot=taxonomy_snapshot()
        expected={"50th Anniversary Range","Hybrid/Electric Vehicles","Cars & Vans",
                  "HGV & PSV","Motorcycle","Bicycles","General Hand Tools",
                  "Workshop","Consumables","Assorted Boxes","Spares","New Products"}
        self.assertEqual(set(TAXONOMY),expected)
        self.assertGreater(snapshot["category_path_count"],300)
        self.assertFalse(snapshot["index_is_complete"])
        self.assertEqual(snapshot["source"],SOURCE_URL)
        self.assertEqual(snapshot["snapshot_date"],SNAPSHOT_DATE)
        for top, groups in TAXONOMY.items():
            paths=[[top]]
            for department, subcategories in groups.items():
                paths.append([top,department])
                paths.extend([top,department,leaf] for leaf in subcategories)
            for path in paths:
                with self.subTest(path=path):
                    plan=marketing_for_path(path)
                    self.assertIn(plan["id"],LENSES)
                    self.assertIn(plan["focus"],("price","benefit","application"))
                    self.assertEqual(len(plan["audiences"]),2)
                    self.assertEqual(len(plan["channels"]),2)
                    self.assertTrue(plan["feature_terms"])
                    self.assertTrue(plan["reason"])

    def test_timing_kit_6200_uses_official_peugeot_leaf(self):
        url=catalogue_url_for_part("6200")
        self.assertIsNotNone(url)
        matched=category_from_product_url(url,"6200")
        self.assertEqual(matched["path"],
                         ["Cars & Vans","Engine Timing Tools","Peugeot"])
        self.assertEqual(matched["marketing"]["id"],"application_fitment")
        self.assertEqual(matched["marketing"]["profile"],"engine_timing")
        self.assertEqual(matched["source"],"verified_official_url")
        self.assertIn("Peugeot",matched["breadcrumb"])

    def test_other_pilot_parts_have_exact_website_subcategories(self):
        cases={
            "9395":("Cars & Vans","Transmission","Wheel Bearings","bearing_suspension"),
            "8324":("Cars & Vans","Steering & Suspension","Shock Absorbers","bearing_suspension"),
            "9372":("Workshop","Equipment","Hydraulic Press","workshop_press"),
            "9197":("Workshop","Inspection - Lighting","Workshop Lamps","lighting_inspection"),
            "9364":("General Hand Tools","Socketry","General Ratchets","socket_ratchet"),
            "9365":("General Hand Tools","Socketry","General Ratchets","socket_ratchet"),
            "9024":("Workshop","Air Tools & Accessories","Air Tools","air_power"),
            "4832":("Cars & Vans","Brakes","Brake Bleeding","workshop_service"),
        }
        for part,(root,dept,leaf,profile) in cases.items():
            with self.subTest(part=part):
                row=category_from_product_url(catalogue_url_for_part(part),part)
                self.assertEqual(row["path"][:3],[root,dept,leaf])
                self.assertEqual(row["marketing"]["profile"],profile)
                self.assertGreaterEqual(len(row["path"]),3)
        self.assertGreaterEqual(len(catalogue_part_index()),10)

    def test_subcategory_strategies_are_different_when_required(self):
        socket=marketing_for_path(["General Hand Tools","Socketry","Socket Sets"])
        pliers=marketing_for_path(["General Hand Tools","Pliers & Grips","Circlip Pliers"])
        press=marketing_for_path(["Workshop","Equipment","Hydraulic Press"])
        timing=marketing_for_path(["Cars & Vans","Engine Timing Tools","Peugeot"])
        ev=marketing_for_path(["Hybrid/Electric Vehicles","Insulated Tools","Socketry"])
        self.assertEqual(socket["id"],"kit_contents")
        self.assertEqual(pliers["id"],"hand_tool_features")
        ratchet=marketing_for_path(["General Hand Tools","Socketry","General Ratchets"])
        individual=marketing_for_path(["General Hand Tools","Socketry","Individual Sockets"])
        socket_storage=marketing_for_path(["General Hand Tools","Socketry","Socket Racks"])
        digital_measure=marketing_for_path(["General Hand Tools","Measuring & Marking","Measuring"])
        induction=marketing_for_path(["Workshop","Equipment","Heat Induction"])
        self.assertEqual(ratchet["id"],"individual_drive_tools")
        self.assertEqual(individual["id"],"individual_drive_tools")
        self.assertEqual(socket_storage["id"],"storage_organisation")
        self.assertEqual(digital_measure["id"],"measurement_specs")
        self.assertEqual(induction["id"],"equipment_specifications")
        self.assertNotEqual(induction["id"],press["id"])
        self.assertEqual(press["id"],"capacity_equipment")
        self.assertEqual(timing["id"],"application_fitment")
        self.assertEqual(ev["id"],"ev_safety")
        self.assertEqual(ev["channels"],["email","website"])

    def test_url_matches_part_and_rejects_other_sites_or_wrong_skus(self):
        source=catalogue_url_for_part("6200")
        for invalid,part in [
            (source,"9395"),(source.replace("www.toolconnection.co.uk","fake-site.co.uk"),"6200"),
            (source.replace("https:","http:"),"6200"),
            ("https://www.toolconnection.co.uk/products/general-hand-tools","6200"),
            ("https://www.toolconnection.co.uk/products/general-hand-tools/socketry/6201-new-tool","6200"),
        ]:
            self.assertIsNone(category_from_product_url(invalid,part))
        unknown=("https://www.toolconnection.co.uk/products/general-hand-tools/"
                 "socketry/socket-sets/12345-demo-product")
        row=category_from_product_url(unknown,"12345")
        self.assertEqual(row["path"],["General Hand Tools","Socketry","Socket Sets"])
        self.assertEqual(row["marketing"]["id"],"kit_contents")
        self.assertIsNone(catalogue_url_for_part("12345"))

    def test_product_lookup_gets_verified_hierarchy_while_pdf_does_not(self):
        product={
            "part":"6200",
            "title":"Engine Timing Kit for PSA",
            "description":"A genuine manufacturer-described timing tool.",
            "features":[
                "Designed to hold the camshafts and crankshaft in their timed position during belt replacement.",
                "For PSA, Peugeot and Vauxhall/Opel 1.0 and 1.2 litre engines.",
            ],
            "specs":{}, "price":None,
            "source":catalogue_url_for_part("6200"),
        }
        actual=apply_official_taxonomy(product)
        self.assertEqual(actual["official_taxonomy"]["department"],"Engine Timing Tools")
        self.assertEqual(detect_category(actual),
                         ("engine_timing","official manufacturer product-category URL"))
        direction=strategy_for(actual)
        self.assertEqual(direction["site_category_path"][:3],
                         ["Cars & Vans","Engine Timing Tools","Peugeot"])
        plan=explain_strategy(actual)
        self.assertIn("Peugeot",plan["category_label"])
        self.assertEqual(plan["marketing_lens"]["id"],"application_fitment")
        self.assertEqual(plan["primary_focus"],"application")
        self.assertIn(plan["proof_point"],actual["features"])
        self.assertTrue(plan["review_required"])
        self.assertEqual(plan["official_category_source"],"verified_official_url")
        self.assertEqual(strategy_options(actual)["audiences"][0]["id"],
                         "category_audience_0")
        # A manufacturer's PDF can provide verified features but not a
        # verified website category URL: don't mark it as official.
        sheet=dict(product,source="https://www.lasertools.co.uk/pis/6200_PIS.pdf")
        self.assertNotIn("official_taxonomy",apply_official_taxonomy(sheet))
        self.assertEqual(explain_strategy(sheet)["official_category_path"],[])

    def test_import_company_urls_in_bulk_and_report_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            csv_path=folder/"products.csv"
            index_path=folder/"catalogue_index.json"
            with csv_path.open("w",encoding="utf-8",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=["Part Number","Official URL"])
                writer.writeheader()
                writer.writerow({"Part Number":"6200","Official URL":catalogue_url_for_part("6200")})
                writer.writerow({"Part Number":"9372","Official URL":catalogue_url_for_part("9372")})
                writer.writerow({"Part Number":"9999","Official URL":"https://wrong.example/9999"})
                writer.writerow({"Part Number":"6200","Official URL":catalogue_url_for_part("6200")})
                writer.writerow({"Part Number":"6200","Official URL":catalogue_url_for_part("9372")})
            audit=import_catalogue_csv(csv_path,index_path,preserve_existing=False)
            self.assertEqual(audit["summary"]["rows_seen"],5)
            self.assertEqual(audit["summary"]["new_parts"],2)
            self.assertEqual(audit["summary"]["already_indexed"],1)
            self.assertEqual(audit["summary"]["unresolved"],2)
            output=json.loads(index_path.read_text(encoding="utf-8"))
            self.assertFalse(output["catalogue_complete"])
            self.assertEqual(set(output["products"]),{"6200","9372"})
            self.assertEqual(len(audit["unresolved_rows"]),2)
            # A second run must not erase successful existing mappings.
            second=import_catalogue_csv(csv_path,index_path)
            self.assertEqual(second["summary"]["total_indexed"],2)
            self.assertEqual(second["summary"].get("new_parts",0),0)

    def test_catalogue_endpoint_and_optional_browser(self):
        client=studio.app.test_client()
        response=client.get("/api/catalogue/taxonomy")
        self.assertEqual(response.status_code,200)
        tree=response.get_json()
        self.assertGreater(tree["category_path_count"],300)
        self.assertFalse(tree["index_is_complete"])
        self.assertGreaterEqual(tree["part_numbers_indexed"],10)
        page=studio.V7_HOME_PAGE
        for name in ("taxonomyExplorer","taxonomySearch","taxonomyMatches",
                     "strategyCategorySource","strategyLens"):
            self.assertEqual(page.count('id="'+name+'"'),1)
        self.assertIn("function flattenTaxonomy(data)",page)
        self.assertIn("/api/catalogue/taxonomy",page)
        self.assertIn("v40-catalogue-hierarchy",page)


if __name__=="__main__":
    unittest.main()

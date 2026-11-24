"""V85 sales assistant: no renderer, no invented claims, bounded model plan."""
import unittest
from unittest.mock import patch
import app as studio
from sales_assistant import build_sales_brief

PRODUCT={"part":"9395","title":"Front Wheel Bearing Kit - for Mercedes-Benz Sprinter & VW Crafter","features":["Kit includes extraction & insertion clamshells.","Applications include Mercedes-Benz Sprinter (2006 - 2019)."],"specs":{},"source":"https://www.lasertools.co.uk/product/9395","price":"£630.79 including VAT"}

class SalesAssistantTests(unittest.TestCase):
    def test_offline_brief(self):
        a=build_sales_brief(PRODUCT,"fleet",use_ai=False)
        b=build_sales_brief(PRODUCT,"distributor",use_ai=False)
        self.assertNotEqual(a["pitch"],b["pitch"])
        self.assertEqual(a["method"],"verified-source")
        self.assertTrue(set(a["selling_points"]).issubset(PRODUCT["features"]))
        self.assertEqual(a["source"],PRODUCT["source"])
        self.assertEqual(len(a["objections"]),3)
        self.assertTrue(a["review_required"])

    def test_model_can_select_only_valid_fact_ids(self):
        with patch.dict("os.environ",{"GEMINI_API_KEY":"test"}), patch("sales_assistant._gemini_json",return_value={"fact_ids":[1,True,999,0,1],"claim":"Guaranteed 500% better"}):
            a=build_sales_brief(PRODUCT,"workshop")
        self.assertEqual(a["method"],"gemini-assisted")
        self.assertEqual(len(a["selling_points"]),2)
        self.assertNotIn("500%",str(a))

    def test_v86_different_products_have_different_conversations(self):
        lamp={**PRODUCT,"part":"9197","title":"Rechargeable Under Bonnet Lamp","features":["LED lamp with adjustable brightness.","Rechargeable battery.","Adjustable working length."]}
        ratchet={**PRODUCT,"part":"9365","title":"Ratchet Set 4pc","features":["Four ratchets with different drive sizes.","60 tooth ratchet mechanism.","Supplied in a storage case."]}
        other_bearing={**PRODUCT,"part":"0001","title":"Bearing Removal Kit","features":["Hydraulic extraction capacity: 10 tonnes.","Supplied with adapters."]}
        results=[build_sales_brief(p,"workshop",use_ai=False) for p in (PRODUCT,lamp,ratchet,other_bearing)]
        self.assertEqual(len({r["questions"][0] for r in results[:3]}),3)
        self.assertEqual(len({r["objections"][0]["objection"] for r in results[:3]}),3)
        self.assertEqual(len({r["closing"] for r in results[:3]}),3)
        self.assertNotEqual(results[0]["objections"],results[3]["objections"])
        for result in results:
            self.assertTrue(result["demonstration_plan"])
            self.assertEqual(len(result["objections"]),3)

    def test_v86_model_cannot_invent_conversation_themes(self):
        with patch.dict("os.environ",{"GEMINI_API_KEY":"test"}), patch("sales_assistant._gemini_json",return_value={"fact_ids":[0],"theme_ids":["invented guarantee","lighting","extraction"]}):
            result=build_sales_brief(PRODUCT,"workshop")
        self.assertNotIn("invented guarantee",str(result))
        self.assertNotIn("light output",str(result))
        self.assertIn("puller",result["objections"][0]["objection"])

    def test_endpoint_without_artwork(self):
        with patch.object(studio,"_sales_product_record",return_value=PRODUCT), patch.object(studio,"lookup",side_effect=AssertionError("Image lookup not permitted")), patch.object(studio,"build_campaign",side_effect=AssertionError("Artwork not permitted")), patch.dict("os.environ",{"GEMINI_API_KEY":""}):
            client=studio.app.test_client()
            r=client.post("/api/sales-assistant/9395",json={"audience":"fleet"})
            self.assertEqual(r.status_code,200,r.get_data(as_text=True))
            self.assertEqual(r.get_json()["part"],"9395")
            self.assertEqual(client.post("/api/sales-assistant/9395",json={"audience":"unknown"}).status_code,400)
            self.assertEqual(client.post("/api/sales-assistant/9395",json={"audience":"fleet","price":"£1"}).status_code,400)
    def test_v87_8899_cold_lookup_uses_verified_record_without_artwork(self):
        with patch.object(studio,"CACHE",{}), patch.object(studio,"official_get",side_effect=studio.LookupErrorPublic("Source unavailable")), patch.dict("os.environ",{"GEMINI_API_KEY":""}):
            response=studio.app.test_client().post("/api/sales-assistant/8899",json={"audience":"dealer"})
        self.assertEqual(response.status_code,200,response.get_data(as_text=True))
        data=response.get_json()
        self.assertEqual(data["part"],"8899")
        self.assertTrue(data["selling_points"])
        self.assertIn("ball joint",data["title"].lower())
        self.assertIn("8899",data["source"])

    def test_v87_pdf_text_only_skips_image_extraction(self):
        import fitz
        doc=fitz.open()
        page=doc.new_page()
        for i,line in enumerate(("8899","Ball Joint Separator for JLR","Additional Information","- Heavy-duty scissor type separator.")):
            page.insert_text((60,70+i*22),line)
        data=doc.tobytes()
        doc.close()
        with patch.object(studio.Image,"open",side_effect=AssertionError("No images may be opened")):
            record,photo=studio.parse_pis_pdf(data,"8899","https://www.lasertools.co.uk/pis/8899_PIS.pdf",include_photo=False)
        self.assertIsNone(photo)
        self.assertEqual(record["part"],"8899")
        self.assertTrue(record["features"])

    def test_v88_unknown_sku_uses_discovery_without_images(self):
        from types import SimpleNamespace
        part="123456"
        url="https://www.toolconnection.co.uk/products/workshop/"+part+"-test-tool"
        product={"part":part,"title":"Workshop Inspection Lamp","description":"Inspection lamp for workshop tasks.","features":["LED lamp with adjustable brightness."],"specs":{},"price":"£20 including VAT","source":url}
        with patch.object(studio,"CACHE",{}), patch.object(studio,"catalogue_url_for_part",return_value=None), patch.object(studio,"search_official_uk_product",return_value=url) as discover, patch.object(studio,"official_get",return_value=SimpleNamespace(content=b"html",url=url)), patch.object(studio,"parse_html",return_value=product), patch.object(studio,"valid_image",side_effect=AssertionError("Image processing forbidden")), patch.dict("os.environ",{"GEMINI_API_KEY":""}):
            response=studio.app.test_client().post("/api/sales-assistant/"+part,json={"audience":"workshop"})
            discover.assert_called_once()
            self.assertEqual(response.status_code,200,response.get_data(as_text=True))
            self.assertEqual(response.get_json()["part"],part)
            self.assertNotIn(part,studio.CACHE)

    def test_ui(self):
        self.assertIn('id="salesAssistant"',studio.V7_HOME_PAGE)
        self.assertIn("sales_assistant.js?v=88",studio.V7_HOME_PAGE)

if __name__=="__main__":
    unittest.main()

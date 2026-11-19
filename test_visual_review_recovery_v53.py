"""V53 regressions: never approve rejected AI artwork or show stale failures."""
import unittest
from unittest.mock import patch

import app as studio
from campaign_hub import build_campaign
from test_ai_creative_director_v45 import PRODUCT, PRICE, SMART, TECH, image_bytes

POSTERS=("poster_technical","poster_price","poster_smart")


def critic(codes=(), *, reviewed=True):
    return {
        "method":"mock-independent-vision",
        "reviewed":reviewed,
        "issues":{role:(list(codes) if role=="poster_technical" else [])
                  for role in POSTERS},
        "warning":None,
    }


class VisualReviewRecoveryV53Tests(unittest.TestCase):
    def setUp(self):
        self.photo=image_bytes()
        self.seen=[]
        self.events=[]
        self.png=image_bytes(1200,1500)

    def select(self, render, role, source, **kwargs):
        variation=kwargs.get("variants",(1,))[0]
        self.seen.append((role,variation,source==self.photo))
        output,_geometry=render(variation)
        return output,{"passed":True,"score":92,"variation":variation,
                       "candidates_checked":1,"issues":[],"warnings":[]}

    def run_campaign(self, reviews):
        with patch("campaign_hub._concepts",return_value=(
                [{"creative_canvas":PRICE},{"creative_canvas":SMART},
                 {"creative_canvas":TECH}],"gemini-assisted",[])), \
             patch("campaign_hub.require_good_asset",return_value={"passed":True}), \
             patch("campaign_hub.find_scene",return_value=(
                 None,{"source":"No external photograph used","category":"hand_tools"})), \
             patch("campaign_hub.choose_best",side_effect=self.select), \
             patch("campaign_hub.render_creative_canvas",return_value=self.png), \
             patch("campaign_hub.technical_poster",return_value=self.png), \
             patch("campaign_hub.smart_poster",return_value=self.png), \
             patch("campaign_hub.render_promo",return_value=self.png), \
             patch("campaign_hub.review_finished_artworks",side_effect=reviews) as vision, \
             patch("campaign_hub.check_distinctness",return_value={
                 "passed":True,"issues":[],"pairs":[]}):
            result=build_campaign(PRODUCT,self.photo,use_gemini=True,
                                  progress=lambda *args:self.events.append(args))
            return result,vision.call_count

    def test_two_alternative_layouts_can_rescue_a_rejected_poster(self):
        pack,count=self.run_campaign([
            critic(["cutoff_text"]),critic(["unreadable_copy"]),critic([])])
        self.assertEqual(count,3)
        self.assertEqual(
            [variant for role,variant,genuine in self.seen
             if role=="technical_application"],[1,2,0])
        self.assertTrue(all(genuine for _,_,genuine in self.seen))
        quality=pack["manifest"]["artwork_quality"]["poster_technical"]
        self.assertEqual(quality["visual_repair_attempt"],2)
        self.assertTrue(quality["auto_repaired"])
        self.assertTrue(any(event[0]=="ready" and event[1]=="poster_technical"
                            for event in self.events))

    def test_persistent_rejection_names_specific_visual_fault(self):
        with self.assertRaisesRegex(ValueError,
                                    "poster_technical: cutoff_text"):
            self.run_campaign([
                critic(["cutoff_text"]),critic(["cutoff_text"]),
                critic(["cutoff_text"]),critic(["cutoff_text"])])
        self.assertEqual(
            [variant for role,variant,_ in self.seen
             if role=="technical_application"][:3],[1,2,0])
        self.assertFalse(any(event[0]=="ready" and event[1] in POSTERS
                             for event in self.events))

    def test_source_photo_defect_is_never_bypassed(self):
        with self.assertRaisesRegex(ValueError,
                                    "poster_technical: white_halo"):
            self.run_campaign([critic(["white_halo"])])
        self.assertEqual(
            [variant for role,variant,_ in self.seen
             if role=="technical_application"],[1])
        self.assertFalse(any(event[0]=="ready" and event[1] in POSTERS
                             for event in self.events))

    def test_failed_job_reports_real_reason_not_a_false_running_state(self):
        client=studio.app.test_client()
        with studio.CAMPAIGN_JOBS_LOCK:
            studio.CAMPAIGN_JOBS.clear()
        with patch("app.threading.Thread"):
            started=client.post("/api/campaign/start/6330",json={})
        self.assertEqual(started.status_code,202)
        job_id=started.get_json()["job_id"]
        with patch("app._assemble_campaign_bundle",
                   side_effect=ValueError(
                       "AI visual review could not approve the posters: "
                       "poster_technical: cutoff_text")):
            studio._run_campaign_job(job_id,"6330",{})
        result=client.get("/api/campaign/jobs/"+job_id).get_json()
        self.assertEqual(result["status"],"failed")
        self.assertEqual(result["stage"],"failed")
        self.assertEqual(result["ready_count"],0)
        self.assertIn("poster_technical: cutoff_text",result["error"])
        with studio.CAMPAIGN_JOBS_LOCK:
            studio.CAMPAIGN_JOBS.clear()

    def test_dashboard_displays_terminal_failure_and_clears_recovery(self):
        page=studio.V7_HOME_PAGE
        self.assertIn("const failed=data.status==='failed';",page)
        self.assertIn("status=failed&&oldStatus!=='ready'",page)
        self.assertIn("'Campaign stopped: '+failureReason",page)
        self.assertIn("'Quality review stopped: '",page)
        self.assertIn("sessionStorage.removeItem(CAMPAIGN_RESUME_KEY)",page)
        self.assertIn("updateCampaignRecovery();",page)


if __name__=="__main__":
    unittest.main()

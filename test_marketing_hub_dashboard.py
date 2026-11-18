"""Dashboard V33 markup and interaction smoke tests.

The visual shell must not remove or duplicate the underlying campaign inputs,
copy editor, customer branding, AI editor or export controls.
"""
import re
import unittest
import app as studio


class MarketingHubDashboardTests(unittest.TestCase):
    def test_approved_dashboard_navigation_and_sections(self):
        html=studio.V7_HOME_PAGE
        for identifier in ('builder','studioWorkspace','assetWorkspace','copyWorkspace',
                           'savedPromotions','productStudio','campaignSettings',
                           'campaignBtn','campaignStatus','previews','campaignResults',
                           'record','searchForm','searchBtn','generateAI',
                           'unifiedCopyStudio','campaignCopyText','campaignDownload',
                           'download','reviewed'):
            self.assertEqual(html.count('id="'+identifier+'"'),1,identifier)
        self.assertIn('class="studio-sidebar"',html)
        self.assertIn('Build a Unique Product Campaign',html)
        self.assertIn('Saved Promotions Library',html)
        self.assertIn('Coming soon',html)
        self.assertNotIn('24 Saved Promotions',html)
        self.assertNotIn('132 Product Assets',html)
        self.assertIn('no campaigns are being stored by this demo',html)

    def test_single_editor_and_live_campaign_preserved(self):
        html=studio.V7_HOME_PAGE
        self.assertEqual(len(re.findall(r'<textarea\s+id="campaignCopyText"',html)),1)
        self.assertNotIn('id="aiCopyText"',html)
        self.assertIn('function installMarketingHubLayout()',html)
        self.assertIn("assets.appendChild($('previews'))",html)
        self.assertIn("copy.appendChild($('unifiedCopyStudio'))",html)
        self.assertIn("$('campaignBtn').click()",html)
        self.assertIn("$('searchBtn').addEventListener('click'",html)
        self.assertIn("const response=await fetch('/api/campaign/'",html)
        self.assertIn("data-open-ai",html)
        self.assertIn("showCopyEmpty()",html)
        self.assertIn("previewDialog)document.body.appendChild",html)

    def test_dashboard_is_served(self):
        response=studio.app.test_client().get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'Build a Unique Product Campaign',response.data)
        self.assertIn(b'Saved Promotions Library',response.data)
        self.assertIn(b'campaignCopyText',response.data)
        self.assertIn(b'static/styles.css?design=v41-unified-campaign',response.data)


if __name__=='__main__':
    unittest.main()

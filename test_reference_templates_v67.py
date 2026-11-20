"""Regression checks for the two approved role-specific Laser templates."""
import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from poster_quality import capture, record_product
from reference_poster_templates import render_technical_reference, render_promo_reference


class ReferenceTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        picture = Image.new("RGBA", (800, 470), (0, 0, 0, 0))
        d = ImageDraw.Draw(picture)
        d.rounded_rectangle((42, 35, 758, 429), radius=43,
                            fill=(88, 102, 116, 255))
        buffer = io.BytesIO()
        picture.save(buffer, "PNG")
        cls.photo = buffer.getvalue()

    def sample(self, part="9395", title="Front Wheel Bearing Kit", price="£175.00 ex VAT"):
        return {
            "part": part, "title": title, "price": price,
            "features": [
                "Applications include: Mercedes-Benz Sprinter and Volkswagen Crafter.",
                "Press front wheel bearings with a standard workshop press.",
                "Kit includes extraction and insertion clamshells.",
                "Refer to the official tool documentation before use.",
            ],
        }

    def fake_photo(self, canvas, blob, bounds, scale=1.0):
        original = Image.open(io.BytesIO(blob)).convert("RGBA")
        original.thumbnail((int((bounds[2]-bounds[0]) * .86),
                            int((bounds[3]-bounds[1]) * .86)),
                           Image.Resampling.LANCZOS)
        x = (bounds[0]+bounds[2]-original.width)//2
        y = (bounds[1]+bounds[3]-original.height)//2
        canvas.alpha_composite(original, (x, y))
        record_product((x,y,x+original.width,y+original.height),
                       original.width*original.height/(1200*1500), True)

    def output(self, renderer, product):
        concept = {
            "campaign_role": "technical_application" if renderer is render_technical_reference
                             else "price_promo",
            "selling_point": product["features"][1],
            "features": list(product["features"]),
        }
        with patch("reference_poster_templates.product_photo",
                   side_effect=self.fake_photo):
            with capture() as record:
                raw = renderer(product, self.photo, concept)
        image = Image.open(io.BytesIO(raw))
        image.load()
        return image, record, raw

    def test_technical_reference_is_real_detailed_sheet(self):
        image,record,_ = self.output(render_technical_reference,self.sample())
        self.assertEqual(image.size,(1200,1500))
        self.assertEqual(image.getpixel((12,260)),(255,255,255))
        roles = [t["role"] for t in record.texts]
        self.assertIn("headline",roles)
        self.assertIn("section_heading",roles)
        self.assertIn("detail",roles)
        self.assertTrue(record.products)
        self.assertFalse(any(t["truncated"] for t in record.texts))
        self.assertTrue(any("Applications include:" in t["text"] for t in record.texts))

    def test_workshop_promo_has_fact_panels_and_verified_price(self):
        image,record,_=self.output(render_promo_reference,self.sample())
        self.assertEqual(image.size,(1200,1500))
        self.assertEqual(image.getpixel((11,20)),(2,16,31))
        phrases=[t["text"] for t in record.texts]
        self.assertIn("KEY FEATURES",phrases)
        self.assertIn("KIT CONTENTS",phrases)
        self.assertIn("£175.00",phrases)
        self.assertFalse(any(t["truncated"] for t in record.texts))

    def test_no_false_kit_contents_or_invented_rrp(self):
        product=self.sample(price="")
        product["features"]=[x for x in product["features"] if not x.startswith("Kit includes")]
        _,record,_=self.output(render_promo_reference,product)
        texts=[t["text"] for t in record.texts]
        self.assertNotIn("KIT CONTENTS",texts)
        self.assertIn("PRICE ON REQUEST",texts)

    def test_long_name_is_fitted_without_ellipsis(self):
        product=self.sample(part="4554",title=(
            "Metric and Imperial Workshop Tap and Die Set with Assorted "
            "Precision Thread-Cutting Tools"))
        for renderer in (render_technical_reference,render_promo_reference):
            _,record,_=self.output(renderer,product)
            self.assertFalse(any(t["truncated"] for t in record.texts))

    def test_two_roles_do_not_render_as_identical_posters(self):
        product=self.sample()
        _,_,tech=self.output(render_technical_reference,product)
        _,_,promo=self.output(render_promo_reference,product)
        self.assertNotEqual(tech,promo)


if __name__=="__main__":
    unittest.main()

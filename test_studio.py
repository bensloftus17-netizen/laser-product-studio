"""Local/CI smoke tests for verified prices, English copy and three distinct PNG formats."""
import io
import unittest
from PIL import Image, ImageDraw
from app import (manufacturer_price_from_html, english_only_features, with_reviewed_price,
                 manufacturer_gallery_urls, pdf_render_photo, valid_image)
from poster import render_hero, render_technical, render_price, prepared_price

class MarketingStudioSmokeTests(unittest.TestCase):
    def sample(self):
        im=Image.new('RGB',(360,470),'white')
        draw=ImageDraw.Draw(im)
        draw.rounded_rectangle((130,48,230,340),radius=16,fill='#092746')
        draw.rectangle((157,72,205,287),fill='#1d84cd')
        with io.BytesIO() as buf:
            im.save(buf,'PNG')
            photo=buf.getvalue()
        product={
          'part':'9197','title':'9197 Under Bonnet Compact Work Lamp',
          'description':'Magnetic work lamp for hands-free inspection.',
          'features':['Magnetic ends allow hands-free use.',
                      '10W LED output with adjustable settings.',
                      'USB-C rechargeable battery.'],
          'specs':{'Power':'10W','Length':'500mm','Battery':'4400mAh'},
          'price':'£48.78 excluding VAT','source':'Official UK manufacturer listing'
        }
        return product,photo

    def test_price_parsing(self):
        self.assertEqual(
            manufacturer_price_from_html('<h1>Product</h1><p>RRP£114.70plus VAT</p>'),
            '£114.70 excluding VAT'
        )
        self.assertEqual(
            manufacturer_price_from_html('<h1>Product</h1><p>RRP£2,617.62inc VAT £2,181.35exc VAT</p>'),
            '£2,617.62 including VAT'
        )
        self.assertIsNone(manufacturer_price_from_html('<p>Special offer £23.99</p>'))

    def test_vat(self):
        p,_=self.sample()
        amount=prepared_price(p)
        self.assertEqual(amount['primary'],'£58.54')
        self.assertEqual(amount['secondary'],'£48.78 EX VAT')
        inc=prepared_price({'price':'£630.79 including VAT'})
        self.assertEqual(inc['secondary'],'£525.66 EX VAT')

    def test_language_and_manual_price(self):
        facts=english_only_features(['Méthode de syphonage unidirectionnelle','2 litre capacity tank.'])
        self.assertEqual(facts,['2 litre capacity tank.'])
        p,_=self.sample()
        reviewed=with_reviewed_price(p,'114.70',True)
        self.assertEqual(prepared_price(reviewed)['primary'],'£137.64')
        self.assertIn('Staff-entered',reviewed['price_status'])

    def test_photo_validation_rejects_broken_banner(self):
        from app import valid_image
        bad=Image.new('RGB',(960,680),'white')
        d=ImageDraw.Draw(bad)
        d.rectangle((0,335,959,388),fill='black')
        with io.BytesIO() as buf:
            bad.save(buf,'PNG')
            self.assertFalse(valid_image(buf.getvalue()))
        p,photo=self.sample()
        self.assertTrue(valid_image(photo))

    def test_manufacturer_gallery_extracts_real_sku_photos(self):
        html=b'''<a href="/items/large/9197.jpg">Studio photo</a>
                   <a href="/items/large/9197_Insitu_1.jpg">Application photo</a>
                   <a href="/items/large/7130.jpg">Other product</a>'''
        class FakeResponse:
            ok=True
            headers={'Content-Type':'text/html'}
            content=html
            def __init__(self,url):self.url=url
        class FakeSession:
            def get(self,url,**kwargs):return FakeResponse(url)
        urls=manufacturer_gallery_urls('9197',FakeSession())
        self.assertEqual(len(urls),2)
        self.assertTrue(any('9197.jpg' in u for u in urls))
        self.assertTrue(any('9197_Insitu_1.jpg' in u for u in urls))

    def test_pdf_composite_photo_fallback(self):
        import fitz
        _,photo=self.sample()
        document=fitz.open()
        pg=document.new_page(width=595,height=842)
        pg.insert_image(fitz.Rect(95,100,400,560),stream=photo)
        pdf=document.tobytes()
        document.close()
        visible=pdf_render_photo(pdf)
        self.assertIsNotNone(visible)
        self.assertTrue(valid_image(visible))

    def test_three_poster_formats(self):
        p,image=self.sample()
        formats=[(render_hero,(1200,1700)),(render_technical,(1280,1590)),(render_price,(1200,1200))]
        for renderer,dimensions in formats:
            with self.subTest(format=renderer.__name__):
                result=renderer(p,image)
                self.assertGreater(len(result),4000)
                with Image.open(io.BytesIO(result)) as graphic:
                    self.assertEqual(graphic.size,dimensions)
        # Manufacturer application photo changes only the campaign graphic.
        in_use=Image.new('RGB',(800,620),'#9BA9B5')
        d=ImageDraw.Draw(in_use)
        d.ellipse((230,150,590,510),fill='#1D2B38')
        with io.BytesIO() as data:
            in_use.save(data,'PNG')
            alternate=render_hero(p,image,data.getvalue())
            self.assertGreater(len(alternate),4000)
            with Image.open(io.BytesIO(alternate)) as graphic:
                self.assertEqual(graphic.size,(1200,1700))


    def test_reference_promo_for_different_skus_and_prices(self):
        p,photo=self.sample()
        names=[
            ('8324','Suspension Split Hub Knuckle Spreader','£41.67 excluding VAT'),
            ('9531','Universal Bearing & Bush Tool Set - 50th Anniversary','£498.00 excluding VAT'),
            ('9372','Air-Hydraulic Workshop Press 50 Tonne','£2,617.62 including VAT'),
            ('9197','Under Bonnet Compact Work Lamp 10W COB Infrared',None),
        ]
        for part,title,rrp in names:
            with self.subTest(part=part):
                custom={**p,'part':part,'title':title,'price':rrp}
                content=render_hero(custom,photo)
                self.assertGreater(len(content),5000)
                with Image.open(io.BytesIO(content)) as image:
                    self.assertEqual(image.size,(1200,1700))

if __name__=='__main__':
    unittest.main()

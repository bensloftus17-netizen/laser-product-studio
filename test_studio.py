"""Local/CI smoke tests for verified prices, English copy and three distinct PNG formats."""
import io
import unittest
from PIL import Image, ImageDraw
from app import (manufacturer_price_from_html, english_only_features, with_reviewed_price,
                 manufacturer_gallery_urls, pdf_render_photo, valid_image, is_french,
                 OFFICIAL_UK_PRODUCTS, VERIFIED_UK_RRP, VERIFIED_UK_FACTS, parse_html,
                 is_non_english, normalise_product_language)
from poster import render_hero, render_technical, render_price, prepared_price, create_fact_sheet_pdf, create_posters, customer_features, campaign_quick_facts, technical_layout_mode

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

    def test_8899_official_english_price_and_no_french(self):
        self.assertIn('8899',OFFICIAL_UK_PRODUCTS)
        self.assertEqual(VERIFIED_UK_RRP['8899'][0],'£144.16 excluding VAT')
        record={'price':VERIFIED_UK_RRP['8899'][0]}
        self.assertEqual(prepared_price(record)['primary'],'£172.99')
        self.assertEqual(prepared_price(record)['secondary'],'£144.16 EX VAT')
        self.assertTrue(is_french('En acier au carbone 45 traité thermiquement.'))
        self.assertTrue(is_french('Méthode de syphonage unidirectionnelle'))
        self.assertFalse(is_french('Manufactured from heat-treated carbon steel.'))
        self.assertFalse(is_french('Land Rover Discovery V L462 and Range Rover IV L405.'))
        self.assertEqual(
            english_only_features(['En acier au carbone 45 traité thermiquement.',
                                   'Scissor-type ball joint separator for JLR.',
                                   'Scissor-type ball joint separator for JLR.']),
            ['Scissor-type ball joint separator for JLR.']
        )
        self.assertGreater(len(VERIFIED_UK_FACTS['8899']['specs']),3)

    def test_staff_rrp_ex_and_inc_vat_inputs(self):
        base={'part':'8899','price':None,'warnings':['UK RRP not verified.']}
        ex=with_reviewed_price(base,'144.16',True,'ex')
        inc=with_reviewed_price(base,'172.99',True,'inc')
        self.assertEqual(prepared_price(ex)['primary'],'£172.99')
        self.assertEqual(prepared_price(inc)['primary'],'£172.99')
        self.assertEqual(prepared_price(inc)['secondary'],'£144.16 EX VAT')
        self.assertIn('Staff-entered',inc['price_status'])
        with self.assertRaises(Exception):
            with_reviewed_price(base,'144.16',False,'ex')
        with self.assertRaises(Exception):
            with_reviewed_price(base,'144.16',True,'bogus')

    def test_uk_html_product_parser_english_price_and_bullets(self):
        page=b"""<html><h1>Ball Joint Separator - for JLR</h1>
           <p>A heavy-duty ball joint separator for Land Rover vehicles suitable for professional workshops.</p>
           <div>8899</div><div>RRP\xc2\xa3144.16plus VAT</div>
           <ul><li>En acier au carbone 45 trait\xc3\xa9 thermiquement.</li>
           <li>Scissor type joint separator for Land Rover Discovery V vehicles.</li></ul></html>"""
        product=parse_html(page,'8899',OFFICIAL_UK_PRODUCTS['8899'])
        self.assertEqual(product['price'],'£144.16 excluding VAT')
        self.assertEqual(product['features'],['Scissor type joint separator for Land Rover Discovery V vehicles.'])

    def test_9024_english_record_and_rrp(self):
        self.assertIn('9024',OFFICIAL_UK_PRODUCTS)
        self.assertEqual(VERIFIED_UK_RRP['9024'][0],'£510.35 excluding VAT')
        self.assertEqual(prepared_price({'price':VERIFIED_UK_RRP['9024'][0]})['primary'],'£612.42')
        record=VERIFIED_UK_FACTS['9024']
        self.assertTrue(record['features'])
        self.assertFalse(any(is_non_english(v) for v in record['features']))

    def test_dutch_and_mixed_language_is_rejected_without_invented_facts(self):
        sentences=[
            '1" slagmoersleutel met buitenmantel in composiet, met verlengde as.',
            'Maximumkoppel van 2170 Nm, met een vernieuwde aandrijving.',
            'Geluidsniveau 98.5 dB. Luchtverbruik 7 cfm.',
            'En acier au carbone 45 traité thermiquement.',
            'Geeignet für Fahrzeuge und Werkzeuge.',
        ]
        for phrase in sentences:
            with self.subTest(phrase=phrase):
                self.assertTrue(is_non_english(phrase),phrase)
        english=[
            'For HGV wheel replacement and workshop maintenance.',
            'Maximum torque 2170Nm, with a 1-inch drive.',
            'Land Rover Discovery V vehicles and BMW models.',
            '10W COB rechargeable lamp with magnetic ends.',
        ]
        for phrase in english:
            with self.subTest(phrase=phrase):
                self.assertFalse(is_non_english(phrase),phrase)
        cleaned=normalise_product_language({
            'title':'Air Impact Wrench 1"D with 6" Anvil',
            'description':'A composite-bodied impact wrench for recessed wheel nuts. 1" slagmoersleutel met een verlengde as.',
            'features':[sentences[0],english[0],sentences[1]],
            'specs':{'Werkdruk':'met een nieuw gereedschap','Drive':'1-inch'},
        })
        self.assertNotIn('slagmoersleutel',cleaned['description'])
        self.assertEqual(cleaned['features'],[english[0]])
        self.assertIn('Drive',cleaned['specs'])
        self.assertNotIn('Werkdruk',cleaned['specs'])

    def test_ratchet_9364_three_piece_vs_9365_four_piece_sources(self):
        self.assertIn('9364',OFFICIAL_UK_PRODUCTS)
        self.assertIn('9365',OFFICIAL_UK_PRODUCTS)
        self.assertEqual(VERIFIED_UK_RRP['9364'][0],'£101.48 excluding VAT')
        self.assertEqual(VERIFIED_UK_RRP['9365'][0],'£178.00 excluding VAT')
        self.assertIn('3',VERIFIED_UK_FACTS['9364']['specs']['Number of pieces'])
        self.assertIn('4',VERIFIED_UK_FACTS['9365']['specs']['Number of pieces'])
        self.assertTrue(all(not is_non_english(x) for x in VERIFIED_UK_FACTS['9364']['features']))
        self.assertTrue(all(not is_non_english(x) for x in VERIFIED_UK_FACTS['9365']['features']))

    def test_adaptive_technical_modes_and_density(self):
        sample,photo=self.sample()
        ratchet3={**sample,
            'part':'9364',
            'title':'9364 Ratchet Set with Comfort Handle 3pc - 50th Anniversary',
            'features':VERIFIED_UK_FACTS['9364']['features'][:],
            'specs':dict(VERIFIED_UK_FACTS['9364']['specs']),
        }
        ratchet4={**sample,
            'part':'9365',
            'title':'9365 Stainless Steel High-Quality Ratchet Set 4pc',
            'features':VERIFIED_UK_FACTS['9365']['features'][:],
            'specs':dict(VERIFIED_UK_FACTS['9365']['specs']),
        }
        bearing={**sample,
            'part':'9395',
            'title':'9395 Front Wheel Bearing Kit - for Mercedes-Benz Sprinter and VW Crafter',
            'features':[
                'Applications: Mercedes-Benz Sprinter and Volkswagen Crafter.',
                'Kit includes extraction and insertion clamshells.',
                'Suitable for use with a standard workshop press.',
                'The bearing is fitted by pressing on the outer race.',
                'Follow the fitting instructions supplied with the kit.',
            ],
            'specs':{
                'Number of pieces':'17',
                'Material':'Steel',
                'Tool type':'Gen 2 wheel bearing fitting kit',
                'Storage':'Metal tin',
                'Vehicle manufacturer':'Mercedes-Benz, Volkswagen',
                'Vehicle model':'Sprinter, Crafter',
            },
        }
        medium={**sample,
            'part':'4832','title':'Manual Pressure Brake Bleeder 2L',
            'features':['2 litre pressure bleeding tank.',
                        'One-way syphoning method.',
                        'Includes pressure release valve.'],
            'specs':{'Capacity':'2 litres','Operating pressure':'10psi'},
        }
        sparse={**sample,
            'part':'9364','title':'Ratchet Set with Comfort Handle 3pc',
            'description':'Set of three workshop ratchets.',
            'features':[],'specs':{},
        }
        for product,mode in [(ratchet3,'light'),(ratchet4,'light'),
                             (bearing,'dense'),(medium,'medium'),(sparse,'light')]:
            with self.subTest(part=product['part'],expected=mode):
                self.assertEqual(technical_layout_mode(product),mode)
                art=render_technical(product,photo)
                self.assertGreater(len(art),5500)
                with Image.open(io.BytesIO(art)) as image:
                    self.assertEqual(image.size,(1280,1590))
        from unittest.mock import patch
        import poster
        with patch.object(poster,'technical_section',wraps=poster.technical_section) as sections:
            render_technical(sparse,photo)
            headings=[str(call.args[4]) for call in sections.call_args_list]
            self.assertIn('PRODUCT OVERVIEW',headings)
            self.assertNotIn('VERIFIED TECHNICAL DATA',headings)
            self.assertFalse(any('FEATURE' in x for x in headings))
        with patch.object(poster,'technical_section',wraps=poster.technical_section) as sections:
            render_technical(bearing,photo)
            headings=[str(call.args[4]) for call in sections.call_args_list]
            self.assertIn('KEY FEATURES',headings)
            self.assertIn('VERIFIED TECHNICAL DATA',headings)
        self.assertTrue(create_fact_sheet_pdf(ratchet3,photo).startswith(b'%PDF'))
        self.assertTrue(create_fact_sheet_pdf(bearing,photo).startswith(b'%PDF'))

    def test_9395_style_technical_png_pdf_and_secondary_photo(self):
        p,blob=self.sample()
        application=Image.new('RGB',(800,600),'#8295A8')
        d=ImageDraw.Draw(application)
        d.rectangle((120,130,730,510),fill='#384A5C')
        with io.BytesIO() as fh:
            application.save(fh,'PNG')
            scene=fh.getvalue()
        for photo in (None,scene):
            with self.subTest(in_use=bool(photo)):
                technical=render_technical(p,blob,photo)
                with Image.open(io.BytesIO(technical)) as image:
                    self.assertEqual(image.size,(1280,1590))
                    # A technical design must be overwhelmingly blue, unlike
                    # the previous white catalogue layout.
                    r,g,b=image.convert('RGB').getpixel((16,580))
                    self.assertGreater(b,r)
                    self.assertGreater(b,g)
                pdf=create_fact_sheet_pdf(p,blob,photo)
                self.assertTrue(pdf.startswith(b'%PDF'))
        assets=create_posters(p,blob,scene)
        self.assertEqual(set(assets),{'Hero','Technical','Price'})

    def test_4554_dutch_kit_list_removed_for_sales_demo(self):
        foreign=[
            'Tappen (2 van elk) en snijbekken, maten M2 x 0,4, M3 x 0,5, M4 x 0,7.',
            '2 x verstelbare taphouders van M6-M20; 2 snijplaathouders.',
            'Gemaakt van gelegeerd staal.',
            'Geleverd in een stevige kunststof behuizing om veilig op te bergen.',
        ]
        for phrase in foreign:
            with self.subTest(phrase=phrase):
                self.assertTrue(is_non_english(phrase))
        p,photo=self.sample()
        p.update(part='4554',
                 title='4554 Metric Tap & Die Set 110pc',
                 description='Professional quality metric tap and die set, featuring split dies, three tap holders and two die holders. Supplied in a blow-moulded storage case.',
                 features=foreign+['Supplied in a blow-moulded storage case.'],
                 price=None,
                 specs={})
        cleaned=normalise_product_language(p)
        self.assertEqual(cleaned['features'],['Supplied in a blow-moulded storage case.'])
        self.assertTrue(all(not is_non_english(x) for x in cleaned['features']))
        self.assertIn('source_raw_features',cleaned)
        assets=create_posters(cleaned,photo)
        self.assertEqual(set(assets),{'Hero','Technical','Price'})
        for name,data in assets.items():
            with self.subTest(poster=name):
                with Image.open(io.BytesIO(data)) as im:
                    self.assertGreater(im.width,1000)

    def test_customer_poster_avoids_long_catalogue_size_lists(self):
        p,photo=self.sample()
        p['features']=[
            'Tap sizes: '+', '.join('M'+str(i)+' x 1mm' for i in range(2,35))+'.',
            'Includes a blow-moulded storage case.',
            'Split dies for metric threads.',
            'Precision thread cutting tools suitable for service work.',
        ]
        points=customer_features(p,5,maxlen=100)
        self.assertTrue(points)
        self.assertTrue(all(len(x)<=100 for x in points))
        self.assertFalse(any('M32 x 1mm' in x for x in points))
        p['title']='4554 Metric Tap & Die Set 110pc'
        chips=campaign_quick_facts(p)
        self.assertIn('110 PIECE METRIC SET',chips)
        self.assertTrue(all(len(x)<43 for x in chips))
        from unittest.mock import patch
        import poster
        p['price']=None
        with patch.object(poster,'txt',wraps=poster.txt) as draws:
            render_hero(p,photo)
            text=[str(c.args[2]) for c in draws.call_args_list if len(c.args)>=3]
            self.assertIn('ON REQUEST',text)
            self.assertNotIn('VERIFY PRICE',text)
        with patch.object(poster,'txt',wraps=poster.txt) as draws:
            render_price(p,photo)
            text=[str(c.args[2]) for c in draws.call_args_list if len(c.args)>=3]
            self.assertIn('ON REQUEST',text)
            self.assertNotIn('NOT VERIFIED',text)

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
        formats=[(render_hero,(1200,1800)),(render_technical,(1280,1590)),(render_price,(1600,980))]
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
                self.assertEqual(graphic.size,(1200,1800))


    def test_v17_guided_homepage_has_working_controls(self):
        from app import app, V7_HOME_PAGE
        from bs4 import BeautifulSoup
        client=app.test_client()
        response=client.get('/')
        self.assertEqual(response.status_code,200)
        document=BeautifulSoup(response.get_data(as_text=True),'html.parser')
        required=('part','searchForm','searchBtn','officialUrl','staffRrp',
                  'staffRrpBasis','staffReview','applyRrp','record','previews',
                  'reviewed','download','status')
        for id_ in required:
            with self.subTest(id=id_):
                self.assertIsNotNone(document.find(id=id_))
        ids=[node.get('id') for node in document.find_all(id=True)]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(document.select('.step[data-step]')),3)
        self.assertEqual(len(document.select('.hero-art .art-sheet')),3)
        self.assertIn('design=v18',V7_HOME_PAGE)
        self.assertIn('function setProgress(stage)',V7_HOME_PAGE)
        self.assertIn('function showPreviews(p,photo)',V7_HOME_PAGE)
        self.assertIn('class="advanced-options"',V7_HOME_PAGE)
        self.assertEqual(client.get('/static/styles.css').status_code,200)

    def test_promo_fitted_text_never_overlaps_price_or_feature_strip(self):
        from unittest.mock import patch
        from PIL import ImageFont
        import poster
        p,photo=self.sample()
        p.update(part='9395',
                 title='9395 Front Wheel Bearing Kit for Mercedes-Benz Sprinter & VW Crafter',
                 description='Front wheel bearings on the Volkswagen Crafter and Mercedes-Benz Sprinter are difficult to remove with the hub in place. Once the hub is removed the bearing can be pressed out and replaced using a standard workshop press.',
                 features=['The bearing can be pressed out and replaced using a standard workshop press.',
                           'Applications: Mercedes Sprinter and Volkswagen Crafter.',
                           'Kit includes bearing fitting and removal adapters.'],
                 price='£525.66 excluding VAT')
        image=Image.new('RGB',(1200,1800),'white')
        d=ImageDraw.Draw(image)
        boxes=[
            ('headline',54,286,1000,300,'FRONT WHEEL BEARING KIT FOR MERCEDES-BENZ SPRINTER & VW CRAFTER'),
            ('benefit',84,1401,535,154,poster.campaign_benefit(p)),
            ('price',832,1391,343,111,'£525.66'),
        ]
        for label,x,y,w,h,text in boxes:
            sizes=(92,86,80,74,68,62,56,50,44,38,32) if label=='headline' else (
                (47,44,41,38,35,32,29,26,23) if label=='benefit' else
                (112,103,94,86,78,71,64,57,50,43,36))
            with self.subTest(panel=label):
                rendered=[]
                def capture(draw,pos,value,size=26,color=None,style='italic',anchor=None):
                    bbox=draw.textbbox((0,0),value,font=poster.font(size,style))
                    rendered.append((pos[0]+bbox[0],pos[1]+bbox[1],
                                     pos[0]+bbox[2],pos[1]+bbox[3],str(value)))
                with patch.object(poster,'txt',side_effect=capture):
                    ok=poster.draw_fitted_panel_copy(
                        d,text,x,y,w,h,sizes,style='italic',
                        colors=['#101417'] if label=='headline' else None,max_lines=3 if label!='price' else 1)
                self.assertTrue(ok)
                self.assertTrue(rendered)
                for left,top,right,bottom,value in rendered:
                    self.assertGreaterEqual(left,x-1,(label,value))
                    self.assertGreaterEqual(top,y-1,(label,value))
                    self.assertLessEqual(right,x+w+1,(label,value))
                    self.assertLessEqual(bottom,y+h+1,(label,value))
                    self.assertNotIn('…',value)
        generated=render_hero(p,photo)
        with Image.open(io.BytesIO(generated)) as im:
            self.assertEqual(im.size,(1200,1800))

    def test_v18_three_authentic_distributor_logos_and_routes(self):
        from app import app, selected_distributor, V7_HOME_PAGE
        from brand_assets import BRAND_LABELS, get_brand_image
        from bs4 import BeautifulSoup
        doc=BeautifulSoup(V7_HOME_PAGE,'html.parser')
        chooser=doc.find(id='distributorBrand')
        self.assertIsNotNone(chooser)
        self.assertEqual([v.get('value') for v in chooser.select('option')],
                         ['none','gsf','euro','mpd'])
        self.assertIsNotNone(doc.find(id='distributorPreview'))
        self.assertIn('function updateDistributorPreview()',V7_HOME_PAGE)
        self.assertIn('distributor_brand:selectedDistributor()',V7_HOME_PAGE)
        self.assertIn('design=v18',V7_HOME_PAGE)
        self.assertIsNone(selected_distributor('none'))
        with self.assertRaises(ValueError):
            selected_distributor('../secrets')
        client=app.test_client()
        for code in ('gsf','euro','mpd'):
            with self.subTest(distributor=code):
                self.assertEqual(selected_distributor(code),code)
                logo=get_brand_image(code)
                self.assertIsNotNone(logo)
                self.assertGreater(logo.width,100)
                self.assertGreater(logo.height,45)
                self.assertIn(code,BRAND_LABELS)
                response=client.get('/api/distributor-logo/'+code)
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.mimetype,'image/png')
                with Image.open(io.BytesIO(response.data)) as image:
                    self.assertEqual(image.size,logo.size)
        self.assertEqual(client.get('/api/distributor-logo/none').status_code,404)
        self.assertEqual(client.get('/api/distributor-logo/../../bad').status_code,404)

    def test_v18_cobrand_posters_and_zip_export(self):
        from app import app, selected_distributor
        from unittest.mock import patch
        import app as app_module
        import json,zipfile
        p,photo=self.sample()
        # Every customer choice alters all three poster outputs and not
        # the underlying genuine product photo or manufacturer facts.
        original=create_posters(p,photo)
        for brand in ('gsf','euro','mpd'):
            with self.subTest(brand=brand):
                assets=create_posters(p,photo,distributor_brand=brand)
                self.assertEqual(set(assets),{'Hero','Technical','Price'})
                for style in ('Hero','Technical','Price'):
                    with self.subTest(format=style):
                        self.assertNotEqual(original[style],assets[style])
                        with Image.open(io.BytesIO(assets[style])) as im:
                            self.assertEqual(im.mode,'RGB')
                branded_pdf=create_fact_sheet_pdf(p,photo,distributor_brand=brand)
                self.assertTrue(branded_pdf.startswith(b'%PDF'))
        client=app.test_client()
        with patch.object(app_module,'lookup',return_value=(p,photo)):
            response=client.post('/api/generate/9197',
                json={'confirmed':True,'distributor_brand':'gsf'})
            self.assertEqual(response.status_code,200)
            with zipfile.ZipFile(io.BytesIO(response.data)) as z:
                names=z.namelist()
                for kind in ('Hero','Technical','Price'):
                    self.assertIn('LASER_9197_'+kind+'.png',names)
                self.assertIn('LASER_9197_Technical_Sheet.pdf',names)
                record=json.loads(z.read('LASER_9197_Source_Record.json'))
                self.assertEqual(record['distributor_brand'],'GSF Car Parts')
                self.assertIn('brand_use_notice',record)
                self.assertTrue(z.read('LASER_9197_Technical_Sheet.pdf').startswith(b'%PDF'))
            failed=client.post('/api/generate/9197',
                json={'confirmed':True,'distributor_brand':'not-listed'})
            self.assertEqual(failed.status_code,400)
            poster=client.get('/api/poster/9197/Hero?distributor_brand=mpd')
            self.assertEqual(poster.status_code,200)
            unbranded=client.get('/api/poster/9197/Hero?distributor_brand=none')
            self.assertEqual(unbranded.status_code,200)
            self.assertNotEqual(poster.data,unbranded.data)

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
                    self.assertEqual(image.size,(1200,1800))

if __name__=='__main__':
    unittest.main()

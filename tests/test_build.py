import importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('build',Path(__file__).parents[1]/'scripts/build.py'); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def issue(user='editor',date='2026-10-20',url='https://news.naver.com/test'):
    return {'number':1,'state':'open','title':'[뉴스브리핑] '+date,'user':{'login':user},'body':'```json\n'+json.dumps({'date':date,'articles':[{'url':url,'title':'<기사>','summary':'요약'}]})+'\n```'}
class BuildTests(unittest.TestCase):
    def test_only_named_editor(self):
        self.assertIsNotNone(m.parse_issue(issue(),['editor']))
        self.assertIsNone(m.parse_issue(issue('outsider'),['editor']))
    def test_closed_excluded(self):
        i=issue();i['state']='closed';self.assertIsNone(m.parse_issue(i,['editor']))
    def test_dates_and_urls(self):
        for date in ['2026-02-30','../../file','20261020']:
            self.assertIsNone(m.parse_issue(issue(date=date),['editor']))
        for url in ['javascript:alert(1)','file:///etc/passwd','https://a:b@example.com/']:
            self.assertIsNone(m.parse_issue(issue(url=url),['editor']))
    def test_duplicate_same_day_and_sort(self):
        one=m.parse_issue(issue(),['editor']);two=m.parse_issue(issue(date='2026-10-19'),['editor'])
        groups=m.group_records([one,one,two],False)
        self.assertEqual([g['date'] for g in groups],['2026-10-20','2026-10-19'])
        self.assertEqual(len(groups[0]['articles']),1)
    def test_metadata_failure(self):
        with patch.object(m,'fetch_metadata',return_value={}):
            record=m.parse_issue(issue(),['editor']);record['articles'][0]['title']='';g=m.group_records([record])[0]
            self.assertIn('제목 미확인',g['articles'][0]['title'])
    def test_metadata_parser(self):
        p=m.MetaParser();p.feed('<title>Fallback</title><meta property="og:title" content="버스 &amp; 정책"><meta property="og:site_name" content="언론사">')
        self.assertEqual(p.meta['og:title'],'버스 & 정책')
    def test_import_photo_and_description(self):
        record=m.parse_issue(issue(),['editor'])
        record['articles'][0]['summary']=''
        with patch.object(m,'fetch_metadata',return_value={'image':'https://example.com/photo.jpg','description':'언론사 기사 소개','source':'언론사'}):
            a=m.group_records([record])[0]['articles'][0]
        self.assertEqual(a['image'],'https://example.com/photo.jpg')
        self.assertEqual(a['summary_kind'],'기사 소개')
        self.assertEqual(a['title'],'<기사>')
    def test_manual_summary_and_photo_take_priority(self):
        record=m.parse_issue(issue(),['editor'])
        record['articles'][0]['image']='https://example.com/manual.jpg'
        with patch.object(m,'fetch_metadata',return_value={'image':'https://example.com/auto.jpg','description':'자동 소개'}):
            a=m.group_records([record])[0]['articles'][0]
        self.assertEqual(a['image'],'https://example.com/manual.jpg')
        self.assertEqual(a['summary'],'요약')
        self.assertNotIn('summary_kind',a)
    def test_relative_og_photo(self):
        class Response:
            headers={'Content-Type':'text/html'}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,*a):return b'<meta property="og:image" content="/photo.jpg">'
            def geturl(self):return 'https://example.com/news/123'
        class Headers(dict):
            def get_content_charset(self):return 'utf-8'
        response=Response();response.headers=Headers(response.headers)
        with patch.object(m,'public_url',return_value='https://example.com'),patch.object(m.urllib.request,'build_opener') as opener:
            opener.return_value.open.return_value=response
            self.assertEqual(m.fetch_metadata('https://example.com/news/123')['image'],'https://example.com/photo.jpg')
    def test_article_body_ignores_menus_and_scripts(self):
        parser=m.MetaParser()
        parser.feed('<nav>광고와 메뉴 내용은 요약에 들어가면 안 됩니다.</nav><div id="dic_area"><script>비밀이 아닌 테스트 스크립트</script><p>부산 시내버스 운행 개선을 위한 새로운 안내 내용이 오늘 공개됐습니다.</p><p>안내 내용은 업체별 의견을 확인한 뒤 현장에 전달할 예정이라고 밝혔습니다.</p><img data-src="/news-photo.jpg"></div><footer>사이트 안내입니다.</footer>')
        summary=m.short_summary(''.join(parser.body[3]))
        self.assertIn('부산 시내버스',summary)
        self.assertNotIn('스크립트',summary)
        self.assertNotIn('메뉴',summary)
        self.assertEqual(parser.images,['/news-photo.jpg'])
    def test_link_only_registration_gets_all_fields(self):
        record=m.parse_issue(issue(),['editor'])
        record['articles']=[{'url':'https://example.com/article'}]
        with patch.object(m,'fetch_metadata',return_value={'title':'자동 제목','source':'언론사','image':'https://example.com/photo.jpg','summary':'자동으로 발췌한 기사 본문입니다.','summary_kind':'본문 자동 발췌'}):
            a=m.group_records([record])[0]['articles'][0]
        self.assertEqual(a['title'],'자동 제목')
        self.assertTrue(a['summary'])
        self.assertTrue(a['image'])
    def test_saved_metadata_survives_future_fetch_failures(self):
        record=m.parse_issue(issue(),['editor'])
        record['articles']=[{'url':'https://example.com/article'}]
        cache={'https://example.com/article':{'title':'보관한 제목','summary':'보관한 요약','image':'https://example.com/photo.jpg'}}
        with patch.object(m,'fetch_metadata') as fetch:
            a=m.group_records([record],cache=cache)[0]['articles'][0]
            fetch.assert_not_called()
        self.assertEqual(a['title'],'보관한 제목')
    def test_never_create_summary_from_title(self):
        record=m.parse_issue(issue(),['editor'])
        record['articles']=[{'url':'https://example.com/article'}]
        with patch.object(m,'fetch_metadata',return_value={'title':'제목만 있음'}):
            self.assertFalse(m.group_records([record])[0]['articles'][0]['summary'])
    def test_social_image_is_in_static_html_with_absolute_url(self):
        config={'title':'뉴스 모음','subtitle':'소식','repository':'o/r','site_url':'https://example.com/news/','share_image':'assets/busan-city-bus.jpg','share_image_width':960,'share_image_height':720}
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            m.build([],config,out,metadata=False)
            parser=m.MetaParser();parser.feed((out/'index.html').read_text())
            self.assertEqual(parser.meta['og:image'],'https://example.com/news/assets/busan-city-bus.jpg')
            self.assertEqual(parser.meta['og:image:width'],'960')
            self.assertEqual(parser.meta['twitter:card'],'summary_large_image')
            self.assertTrue((out/'assets/busan-city-bus.jpg').is_file())
    def test_script_injection(self):
        self.assertNotIn('</script>',m.script_json({'x':'</script><script>alert(1)</script>'}))
    def test_private_address_rejected(self):
        for url in ['http://127.0.0.1/','http://169.254.169.254/','http://[::1]/']:
            with self.assertRaises(ValueError):m.public_url(url)
    def test_pagination(self):
        class Response:
            def __init__(self,x):self.x=x
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self):return json.dumps(self.x).encode()
        with patch.object(m.urllib.request,'urlopen',side_effect=[Response([issue()]*100),Response([])]) as fetch:
            self.assertEqual(len(m.load_issues('o/r','not-real',['editor'])),100)
            self.assertEqual(fetch.call_count,2)
if __name__=='__main__':unittest.main()

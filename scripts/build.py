"""Build GitHub Pages from trusted GitHub issue records. Python standard library only."""
import argparse, base64, datetime as dt, html, ipaddress, json, os, re, shutil, socket, urllib.parse, urllib.request
from pathlib import Path
from html.parser import HTMLParser
ROOT = Path(__file__).resolve().parents[1]

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.title=[]; self.in_title=False
        self.stack=[]; self.body={1:[],3:[]}; self.images=[]; self.headings=[]; self.h1=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='meta':
            key=(a.get('property') or a.get('name') or '').lower()
            if key and a.get('content'): self.meta.setdefault(key,a['content'])
        if tag=='title': self.in_title=True
        if tag=='h1': self.h1=True
        inherited=self.stack[-1][1] if self.stack else 0
        skipped=self.stack[-1][2] if self.stack else False
        marker=(a.get('id','')+' '+a.get('class','')).lower()
        strong=bool(re.search(r'dic_area|articlebody|article[_-](?:body|content|text|view-content)|news[_-](?:body|content|text)|newsct_article|newsview|article_txt',marker)) or a.get('itemprop')=='articleBody'
        scope=3 if strong else (inherited or (1 if tag=='article' else 0))
        skip=skipped or tag in ('script','style','nav','footer','aside','form','button','noscript') or bool(re.search(r'(^|[ _-])(advert|banner|related|comment|copyright|share)([ _-]|$)',marker))
        if tag=='img' and scope and not skip:
            src=a.get('data-src') or a.get('data-original') or a.get('src','')
            if src and not src.startswith('data:'): self.images.append(src)
        if scope and tag in ('p','div','br','li'): self.body[scope].append('\n')
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append((tag,scope,skip))
    def handle_endtag(self, tag):
        if tag=='title': self.in_title=False
        if tag=='h1': self.h1=False
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                scope=self.stack[i][1]
                if scope and tag in ('p','div','article','li'): self.body[scope].append('\n')
                del self.stack[i:]; break
    def handle_data(self, data):
        if self.in_title: self.title.append(data)
        if self.h1: self.headings.append(data)
        if self.stack:
            _,scope,skip=self.stack[-1]
            if scope and not skip: self.body[scope].append(data)

def short_summary(text,limit=230,min_length=25):
    """Extract the article lead; never manufacture a summary from a title."""
    text=html.unescape(text)
    lines=[re.sub(r'\s+',' ',line).strip() for line in text.splitlines()]
    lines=[line for line in lines if len(line)>=min_length and not re.search(r'무단.{0,8}(전재|복제)|재배포.{0,5}금지|관련기사|구독.{0,5}(신청|하기)|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}',line)]
    if not lines: return ''
    joined=' '.join(lines)
    sentences=re.split(r'(?<=[.!?。])\s+|(?<=다\.)',joined)
    result=''
    for sentence in sentences:
        sentence=sentence.strip()
        if not sentence: continue
        if len(result)+len(sentence)>limit:
            if not result:
                cut=sentence[:limit-1]; result=(cut.rsplit(' ',1)[0] if ' ' in cut else cut)+'…'
            break
        result=(result+' '+sentence).strip()
        if len(result)>=100: break
    return result

def safe_url(value):
    try:
        p=urllib.parse.urlsplit(str(value).strip())
        if p.scheme not in ('https','http') or not p.hostname or p.username or p.password: return ''
        if p.port and p.port not in (80,443): return ''
        return urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,p.query,''))
    except ValueError: return ''

def public_url(value):
    value=safe_url(value)
    if not value: raise ValueError('Invalid URL')
    host=urllib.parse.urlsplit(value).hostname
    addresses=socket.getaddrinfo(host,None)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Non-public address')
    return value

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch_metadata(url):
    """Best-effort only; publisher restrictions fall back to editable manual fields."""
    try:
        public_url(url)
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 NewsBrief-LinkPreview/1.0'})
        with urllib.request.build_opener(PublicRedirect).open(request,timeout=8) as response:
            if 'html' not in response.headers.get('Content-Type','').lower(): return {}
            raw=response.read(1_000_000)
            encoding=response.headers.get_content_charset()
            if not encoding:
                match=re.search(br'charset=["\s\x27]*([\w-]+)',raw[:8192],re.I)
                encoding=match.group(1).decode('ascii') if match else 'utf-8'
            p=MetaParser(); p.feed(raw.decode(encoding,errors='replace'))
        body=''.join(p.body[3]).strip() or ''.join(p.body[1]).strip()
        body_summary=short_summary(body)
        summary=body_summary
        description=p.meta.get('og:description') or p.meta.get('description','')
        if not summary: summary=short_summary(description,min_length=8)
        image=p.meta.get('og:image:secure_url') or p.meta.get('og:image') or p.meta.get('twitter:image') or next(iter(p.images),'')
        return {'title':p.meta.get('og:title') or p.meta.get('twitter:title') or ''.join(p.headings) or ''.join(p.title),
                'source':p.meta.get('og:site_name',''),
                'image':safe_url(urllib.parse.urljoin(response.geturl(),image)) if image else '',
                'description':description,'summary':summary,
                'summary_kind':'본문 자동 발췌' if body_summary else '기사 소개'}
    except Exception:
        return {}

def parse_issue(issue, editors=()):
    # An outsider's issue must never become a published news item.
    if issue.get('pull_request') or issue.get('state')!='open': return None
    if issue.get('user',{}).get('login','').lower() not in {x.lower() for x in editors}: return None
    if not issue.get('title','').startswith('[뉴스브리핑]'): return None
    match=re.search(r'```json\s*([\s\S]+?)\s*```',issue.get('body') or '')
    if not match: return None
    try:
        data=json.loads(match.group(1))
        date=data['date']; dt.date.fromisoformat(date)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date): return None
        articles=[]; seen=set()
        for item in data['articles'][:10]:
            url=safe_url(item.get('url',''))
            if not url or url in seen: continue
            seen.add(url)
            articles.append({k:str(item.get(k,'')).strip()[:limit] for k,limit in [('title',250),('summary',1500),('source',100)]}|{'url':url,'image':safe_url(item.get('image',''))})
        if not articles: return None
        return {'date':date,'note':str(data.get('note',''))[:500], 'articles':articles,'issue':issue['number']}
    except (KeyError,TypeError,ValueError,AttributeError): return None

def load_issues(repo,token,editors):
    result=[]; page=1
    while True:
        req=urllib.request.Request(f'https://api.github.com/repos/{repo}/issues?state=open&per_page=100&page={page}',headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'User-Agent':'Busan-NewsBrief'})
        with urllib.request.urlopen(req,timeout=30) as response: batch=json.load(response)
        if not isinstance(batch,list): raise ValueError('Invalid GitHub response')
        for issue in batch:
            parsed=parse_issue(issue,editors)
            if parsed: result.append(parsed)
        if len(batch)<100: break
        page+=1
    return result

def group_records(records,metadata=True,cache=None):
    groups={}; cache={} if cache is None else cache
    for record in sorted(records,key=lambda x:x.get('issue',0)):
        g=groups.setdefault(record['date'],{'date':record['date'],'note':'','articles':[],'issues':[]})
        if record.get('note'): g['note']=record['note']
        if record.get('issue'): g['issues'].append(record['issue'])
        known={a['url'] for a in g['articles']}
        for article in record['articles']:
            a=article.copy()
            if a['url'] in known: continue
            known.add(a['url'])
            if metadata and any(not a.get(k) for k in ('title','source','summary','image')):
                if not cache.get(a['url']):
                    fetched=fetch_metadata(a['url'])
                    if fetched: cache[a['url']]=fetched
                m=cache.get(a['url'],{})
                a['title']=a.get('title') or m.get('title','')
                a['source']=a.get('source') or m.get('source','')
                a['image']=safe_url(a.get('image') or m.get('image',''))
                if not a.get('summary'):
                    a['summary']=m.get('summary') or short_summary(m.get('description',''),min_length=8)
                    if a['summary']: a['summary_kind']=m.get('summary_kind') or '기사 소개'
            a['title']=a.get('title') or '제목 미확인 · 원문에서 확인해 주세요'
            a['source']=a.get('source') or urllib.parse.urlsplit(a['url']).hostname
            a['image']=safe_url(a.get('image',''))
            g['articles'].append(a)
    return sorted(groups.values(),key=lambda x:x['date'],reverse=True)

def script_json(value):
    return json.dumps(value,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')

def build(records,config,out,demo=False,metadata=True,cache=None):
    groups=group_records(records,metadata,cache)
    out.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'assets',out/'assets',dirs_exist_ok=True)
    data={'config':config,'briefs':groups,'demo':demo}
    (out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    css=(ROOT/'assets/style.css').read_text(); js=(ROOT/'assets/app.js').read_text()
    template=(ROOT/'template.html').read_text()
    def page(selected=None,admin=False,standalone=False):
        date=selected['date'] if selected else ''
        title=(date+' 뉴스브리핑 | ' if date else '')+config['title']
        desc=' · '.join(a['title'] for a in selected['articles'][:3]) if selected else config['subtitle']
        base=config.get('site_url','').rstrip('/')
        canonical=base+('/briefs/'+date+'/' if date else '/') if base else ''
        payload=data|{'selectedDate':date,'admin':admin}
        if standalone and config.get('share_image'):
            asset=(ROOT/config['share_image']).read_bytes()
            payload=payload|{'config':config|{'share_image_inline':'data:image/jpeg;base64,'+base64.b64encode(asset).decode()}}
        image_url=urllib.parse.urljoin(base+'/',config.get('share_image','')) if base and config.get('share_image') else config.get('share_image_fallback','')
        social=''
        if image_url:
            social='<meta property="og:site_name" content="'+html.escape(config['title'],quote=True)+'"><meta property="og:locale" content="ko_KR"><meta property="og:image" content="'+html.escape(image_url,quote=True)+'"><meta property="og:image:width" content="'+str(config.get('share_image_width',960))+'"><meta property="og:image:height" content="'+str(config.get('share_image_height',720))+'"><meta property="og:image:alt" content="부산 시내버스"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="'+html.escape(image_url,quote=True)+'">'
        content=template.replace('{{TITLE}}',html.escape(title)).replace('{{DESCRIPTION}}',html.escape(desc,quote=True)).replace('{{URL}}',html.escape(canonical,quote=True))
        content=content.replace('{{SOCIAL_META}}',social).replace('{{CSS}}','<style>'+css+'</style>').replace('{{DATA}}',script_json(payload)).replace('{{JS}}','<script>'+js+'</script>')
        return content
    (out/'index.html').write_text(page())
    (out/'admin.html').write_text(page(admin=True))
    (out/'.nojekyll').touch()
    # One-file preview works directly after download, without a server.
    (ROOT/'preview.html').write_text(page(standalone=True))
    print(f'Built {len(groups)} briefings, {sum(len(g["articles"]) for g in groups)} articles → {out}')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--demo',action='store_true'); ap.add_argument('--no-metadata',action='store_true'); args=ap.parse_args()
    config=json.loads((ROOT/'config.json').read_text())
    repo=os.environ.get('GITHUB_REPOSITORY') or config.get('repository','')
    if repo:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo): raise ValueError('Invalid repository')
        config['repository']=repo
        owner,name=repo.split('/')
        config['site_url']=os.environ.get('PAGES_URL') or config.get('site_url') or f'https://{owner}.github.io/'+('' if name.lower()==f'{owner}.github.io'.lower() else name+'/')
    if args.demo:
        records=json.loads((ROOT/'demo.json').read_text())
    elif os.environ.get('GITHUB_TOKEN') and repo:
        records=load_issues(repo,os.environ['GITHUB_TOKEN'],[repo.split('/')[0]]+config.get('allowed_editors',[]))
    else: records=[]
    cache_path=ROOT/'data/metadata-cache.json'
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    build(records,config,ROOT/'dist',args.demo,not args.no_metadata,cache)
    if not args.demo and not args.no_metadata:
        cache_path.parent.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n')

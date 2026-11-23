"""Local Bilibili intake review. Python 3.9+, no third-party modules."""
import argparse
import fcntl
import hashlib
import html
import json
import os
import re
import sys
import subprocess
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

VERDICTS = {'优先摄入', '工具线索', '待核实', '可跳过', '已有记录'}
BODY = {'subtitle', 'article', 'transcript'}
FIELDS = {'verdict', 'why', 'conf', 'topic', 'form', 'stage', 'refs', 'summary'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode='w', encoding='utf-8') as f:
        f.write(content)
    os.replace(f.name, path)


def get_page(endpoint, params):
    req = Request('https://api.bilibili.com'+endpoint+'?'+urlencode(params),
                  headers={'Referer':'https://www.bilibili.com/', 'User-Agent':'Mozilla/5.0'})
    with urlopen(req, timeout=20) as response:
        payload = json.load(response)
    require(payload['code'] == 0, f"Bilibili code {payload['code']}；保留断点，检查登录或稍后续跑")
    return payload['data']


def inventory(a):
    fid = a.source if a.source.isdecimal() else parse_qs(urlsplit(a.source).query).get('fid',[''])[0]
    require(fid.isdecimal(), '需要收藏夹 fid')
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    rows, page = [], 1
    while True:
        path = cache/f'{fid}-page-{page}.json'
        if path.exists():
            data = load(path)
        else:
            data = get_page('/x/v3/fav/resource/list', dict(media_id=fid, pn=page, ps=40, platform='web'))
            write(path, json.dumps(data,ensure_ascii=False))
            time.sleep(1)
        require(str(data['info']['id']) == fid, '收藏夹 ID 不一致')
        for video in data.get('medias') or []:
            def day(key):
                ts = video.get(key)
                return datetime.fromtimestamp(ts, ZoneInfo(a.timezone)).date().isoformat() if ts else None
            rows.append(dict(bvid=video.get('bvid'), n=len(rows)+1,title=video['title'],
                             author=video['upper']['name'], description=video.get('intro',''),
                             published=day('pubtime'), favorited=day('fav_time'), tags=[], evidence={}))
        if not data['has_more']:
            break
        require(data.get('medias'), '空中间页，目录不完整')
        page += 1
    require(len(rows)==data['info']['media_count'], '条目数与平台声明不符，请检查失效条目与分页缓存')
    validate_items(rows)
    write(a.out,rows)
    return {'folder':fid,'count':len(rows),'pages':page}


def subtitle(a):
    require(bv(a.bvid),'无效 BV')
    cache=Path(a.cache).resolve()
    cache.mkdir(parents=True,exist_ok=True)
    target=cache/(a.bvid+'.P1.md')
    receipt=cache/(a.bvid+'.result.json')
    report=None
    cached=target.exists()
    if cached:
        if receipt.is_file():
            report=load(receipt)
        elif (cache/'batch-state.json').is_file():
            report=load(cache/'batch-state.json')['entries'].get(a.bvid,{}).get('result')
        require(report,'已有字幕缺回执，先核对，不覆盖')
    else:
        skill='bilibili-subtitle-to-markdown'
        homes=[Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'skills'/skill,Path.home()/'.agents/skills'/skill]
        if a.collector:
            homes=[Path(a.collector)]
        script=next((h/'scripts/extract.py' for h in homes if (h/'SKILL.md').is_file() and (h/'scripts/extract.py').is_file()),None)
        require(script,'找不到字幕采集 Skill；传 --collector 安装目录，或用 attach 关联已核验的材料')
        result=subprocess.run([sys.executable,str(script),f'https://www.bilibili.com/video/{a.bvid}/','-o',str(target)],text=True,capture_output=True)
        if not result.stdout.strip():
            raise ValueError(result.stderr[-400:] or '字幕采集器无输出')
        report=json.loads(result.stdout)
        require(result.returncode==0 and report.get('ok'),json.dumps({k:report.get(k) for k in ('status','code','error')},ensure_ascii=False))
    require(report.get('bvid')==a.bvid and report.get('page')==1 and report.get('subtitle_count',0)>0 and
            report.get('count_matches') is True and report.get('timeline_valid') is True and
            report.get('secret_markers') is False and report.get('media_downloaded') is False and
            hashlib.sha256(target.read_bytes()).hexdigest()==report.get('output_sha256'),'字幕回执与文件不一致')
    if not cached:
        write(receipt,report)
    return {'file':str(target),'bvid':a.bvid,'part':1,'segments':report['subtitle_count'],'warning':report.get('warning')}


def match_records(rows, manifest):
    records = {}
    for line in Path(manifest).read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        match = re.search(r'/video/(BV[A-Za-z0-9]{10})(?:[/#?]|$)',record.get('url',''))
        if match:
            records[match[1]] = record
    for row in rows:
        match = records.get(row['bvid'])
        if match:
            source = (Path(manifest).resolve().parent.parent / match['path']).resolve()
            row.setdefault('evidence',{})['registered'] = dict(kind='duplicate', path=str(source), label='已登记：'+match['id'])


def bv(value):
    return isinstance(value,str) and bool(re.fullmatch(r'BV[A-Za-z0-9]{10}',value))


def validate_items(rows):
    require(isinstance(rows,list) and rows,'空目录')
    seen=set()
    for idx,r in enumerate(rows,1):
        b=r['bvid']
        require(bv(b) and b not in seen and r['n']==idx, 'BV 重复、无效或目录顺序不连续')
        seen.add(b)
        require(isinstance(r['title'],str) and r['title'].strip(),'缺少标题')
        for k in ('favorited','published'):
            if r.get(k) is not None:
                date.fromisoformat(r[k])
        require(isinstance(r.get('tags',[]),list) and all(isinstance(t,str) for t in r.get('tags',[])), '无效平台标签')
        for ref,e in r.get('evidence',{}).items():
            require(ref and e['kind'] in BODY|{'metadata','comment','duplicate'},'证据类型错误')
            require(Path(e['path']).is_file() and Path(e['path']).stat().st_size,'本地证据缺失 '+ref)


def token(row):
    value=json.dumps(row,sort_keys=True,ensure_ascii=False)
    for e in row.get('evidence',{}).values():
        value+=hashlib.sha256(Path(e['path']).read_bytes()).hexdigest()
    return hashlib.sha256(value.encode()).hexdigest()


def validate_analysis(row, entry):
    require(set(entry)==FIELDS,'分析字段不完整或夹带人工/未知字段')
    require(entry['verdict'] in VERDICTS and entry['conf'] in {'低','中','高'} and entry['stage'] in {'coarse','deep'},'分析枚举错误')
    for key in ['why','topic','form','summary']:
        require(isinstance(entry[key],str) and (key=='summary' or entry[key].strip()),'无效字段 '+key)
    refs=entry['refs']
    require(isinstance(refs,list) and len(set(refs))==len(refs),'无效证据列表')
    evidence=row.get('evidence',{})
    require(all(ref in evidence for ref in refs),'引用了未知证据')
    if not refs and not row.get('description','').strip().strip('-') and entry['conf']=='高':
        raise ValueError('只有标题和标签时不可高置信')
    kinds={evidence[ref]['kind'] for ref in refs}
    require(entry['verdict']!='优先摄入' or kinds & BODY,'优先摄入须引用正文')
    require(entry['verdict']!='已有记录' or 'duplicate' in kinds,'已有记录须引用查重命中')
    require(not entry['summary'] or kinds & BODY,'不能用评论或元数据生成正文摘要')


def check_decisions(s,d):
    require(d['schema_version']==1 and d['dataset_id']==s['dataset_id'] and type(d['declutter']) is bool,'决定版本、收藏夹或设置不匹配')
    known={r['bvid'] for r in s['rows']}
    require(isinstance(d['decisions'],list),'决定数组无效')
    for i,r in enumerate(d['decisions'],1):
        require(r['bvid'] in known and r['decision'] in {'include','exclude'} and r['revision']==i,'无效决定或未知 BV')
        require(all(isinstance(r[k],str) for k in ('reason','type')),'人评必须为文本')


def report(s, path):
    data=[]
    for r in s['rows']:
        b=r['bvid']; entry=s['analysis'][b]['result']
        refs=[r['evidence'][key] for key in entry['refs']]
        links=[[e.get('label',e['kind']),'./'+os.path.relpath(e['path'],path.parent)] for e in refs]
        body=any(e['kind'] in BODY for e in refs)
        data.append(dict(n=r['n'],bvid=b,title=r['title'],url=f'https://www.bilibili.com/video/{b}/',
                         author=r.get('author',''),tags=r.get('tags',[]),published=r.get('published'),favorited=r.get('favorited'),
                         **{k:entry[k] for k in ('why','verdict','topic','form','conf')},direct=body or entry['verdict']=='已有记录',
                         evidence='、'.join(e.get('label',e['kind']) for e in refs) or '目录初筛',links=links,
                         subSummary=entry['summary'],subStatus='正文摘要' if entry['summary'] else '字幕未抓取到' if r.get('subtitle_status')=='missing' else '暂无正文摘要',
                         subPath=next((l[1] for e,l in zip(refs,links) if e['kind'] in BODY),'')))
    config={k:s[k] for k in ('name','goal','dataset_id','timezone')}
    config.update(declutter=s['human']['declutter'],seed=[[v['bvid'],v['decision']=='include',{'type':v['type'],'reason':v['reason']}] for v in s['human']['decisions']])
    def js(value):
        return json.dumps(value,ensure_ascii=False).replace('<','\\u003c')
    replacements={'ROWS':js(data),'CONFIG':js(config),'NAME':html.escape(s['name']),'DATE':datetime.now(ZoneInfo(s['timezone'])).date().isoformat(),'URL':html.escape(s['url'],quote=True)}
    template=Path(__file__).resolve().parents[1]/'assets/review.html'
    write(path,re.sub(r'@@(ROWS|CONFIG|NAME|DATE|URL)@@',lambda m:replacements[m[1]],template.read_text()))


def execute(a):
    folder=Path(a.run)
    folder.mkdir(parents=True,exist_ok=True)
    state=folder/'state.json'
    if a.cmd=='init':
        require(not state.exists(),'此 run 已存在，请复用或新建目录')
        rows=load(a.input); root=Path(a.input).resolve().parent
        for row in rows:
            for e in row.get('evidence',{}).values():
                e['path']=str((root/e['path']).resolve())
        if a.manifest:match_records(rows,a.manifest)
        validate_items(rows);ZoneInfo(a.timezone)
        require(re.fullmatch(r'[a-zA-Z0-9:_-]+',a.dataset),'无效 dataset ID')
        u=urlsplit(a.url)
        require(u.scheme=='https' and u.hostname in {'space.bilibili.com','www.bilibili.com'},'需要 B 站收藏夹 URL')
        s=dict(schema_version=1,dataset_id=a.dataset,name=a.name,goal=a.goal,url=a.url,timezone=a.timezone,rows=rows,analysis={},
               human=dict(schema_version=1,dataset_id=a.dataset,declutter=True,decisions=[]))
        if a.taxonomy:
            taxonomy=load(a.taxonomy)
            for key in ('topic','form'):
                require(isinstance(taxonomy.get(key),list) and taxonomy[key] and all(isinstance(v,str) for v in taxonomy[key]),'taxonomy 需要 topic/form 字符串列表')
            s['taxonomy']=taxonomy
        write(state,s);return {'items':len(rows)}
    s=load(state)
    require(s['schema_version']==1,'未知状态版本');validate_items(s['rows']);check_decisions(s,s['human'])
    known={r['bvid']:r for r in s['rows']}
    missing=[b for b,r in known.items() if s['analysis'].get(b,{}).get('input_hash')!=token(r)]
    if a.cmd=='attach':
        row=known.get(a.bvid)
        require(row is not None,'未知 BV')
        evidence=dict(kind=a.kind,path=str(Path(a.file).resolve()),label=a.label or a.kind)
        row.setdefault('evidence',{})[a.ref]=evidence
        validate_items(s['rows'])
        write(state,s)
    elif a.cmd=='batch':
        write(a.out,dict(schema_version=1,dataset_id=s['dataset_id'],goal=s['goal'],taxonomy=s.get('taxonomy'),items=[dict(known[b],input_hash=token(known[b])) for b in missing[:a.limit]]))
    elif a.cmd=='merge':
        d=load(a.input)
        require(d['schema_version']==1 and d['dataset_id']==s['dataset_id'],'分析版本或数据集错误')
        if a.batch:
            expected=load(a.batch)
            require(expected['dataset_id']==s['dataset_id'] and {r['bvid'] for r in expected['items']}=={r['bvid'] for r in d['items']},'批次漏项或多项')
        seen=set()
        for e in d['items']:
            b=e['bvid'];require(b in known and b not in seen and e['input_hash']==token(known[b]),'重复、未知或过期分析');seen.add(b)
            if s.get('taxonomy'):
                for key in ('topic','form'):require(e['result'][key] in s['taxonomy'][key], '未批准的分类标签 '+key)
            validate_analysis(known[b],e['result']);s['analysis'][b]={'result':e['result'],'input_hash':e['input_hash']}
        write(state,s)
    elif a.cmd=='import-decisions':
        d=load(a.input);check_decisions(s,d)
        require(not s['human']['decisions'] or s['human']['decisions']==d['decisions'] or a.replace,'已有不同人工决定；先备份再显式 --replace')
        if s['human']!=d:
            write(folder/'decisions.previous.json',s['human']);s['human']=d;write(state,s)
    else:
        require(not missing,f'分析缺失或证据已更新：{missing[:8]}')
        for b,r in known.items():validate_analysis(r,s['analysis'][b]['result'])
        if a.cmd=='render':report(s,Path(a.out).resolve())
        if a.cmd=='export':
            today=date.fromisoformat(a.as_of) if a.as_of else datetime.now(ZoneInfo(s['timezone'])).date()
            votes={v['bvid']:v for v in s['human']['decisions']}
            selected=[]
            for b,r in known.items():
                if votes.get(b,{}).get('decision')!='include':continue
                if s['human']['declutter'] and (not r.get('favorited') or not 0<=(today-date.fromisoformat(r['favorited'])).days<=365):continue
                entry=s['analysis'][b]['result'];body=[r['evidence'][ref]['path'] for ref in entry['refs'] if r['evidence'][ref]['kind'] in BODY]
                selected.append(dict(bvid=b,title=r['title'],url=f'https://www.bilibili.com/video/{b}/',human=votes[b],evidence=body,
                                     status='ready_for_ingest' if body else 'missing_evidence',verdict=entry['verdict'],topic=entry['topic'],form=entry['form'],
                                     author=r.get('author',''),published=r.get('published')))
            write(a.out,dict(instructions='先遵守目标库 AGENTS.md、workflows/ingest.md 和 schemas/content.md。逐条按 BV、工具实体和主题查重。先看 human.type 与 human.reason（人工建议摄入类型与人工备注），明确的人工作为编译意图；未填写时结合 AI 的 topic、form 和实际正文判断。topic 用于检索已有页和选择现有标签。视觉参考须回看作品并留存可追溯的画面证据。缺少可读正文先补采，有正文也要核对其是否支持人评。方法、案例、概念解释和评测先整理登记来源，优先补已有 wiki 页；工具卡按 workflows/catalog.md 核实实体后写 catalog/tools；混合材料可两层互链。补充已有页面先定位目标；自定义类型或证据冲突无法判定时保留待确认。每条记录实际去向、证据和未完成原因。',dataset_id=s['dataset_id'],as_of=today.isoformat(),timezone=s['timezone'],items=selected))
            write(a.urls,''.join(v['url']+'\n' for v in selected))
    return {'command':a.cmd,'items':len(known),'analyzed':len(s['analysis']),'decision_events':len(s['human']['decisions'])}


def main():
    cli=argparse.ArgumentParser(description=__doc__);sub=cli.add_subparsers(dest='cmd',required=True)
    for cmd in ('inventory','subtitle','init','attach','batch','merge','validate','render','import-decisions','export'):
        p=sub.add_parser(cmd)
        if cmd not in {'inventory','subtitle'}:p.add_argument('--run',required=True)
        if cmd in {'init','merge','import-decisions'}:p.add_argument('--input',required=True)
        if cmd in {'inventory','batch','render','export'}:p.add_argument('--out',required=True)
        if cmd in {'init','inventory'}:p.add_argument('--timezone',default='Asia/Shanghai')
        if cmd=='subtitle':
            p.add_argument('--bvid',required=True);p.add_argument('--cache',required=True);p.add_argument('--collector')
        if cmd=='inventory':
            p.add_argument('--source',required=True);p.add_argument('--cache',required=True)
        if cmd=='init':
            for k in ('dataset','name','goal','url'):p.add_argument('--'+k,required=True)
        if cmd=='init':
            p.add_argument('--manifest')
            p.add_argument('--taxonomy')
        if cmd=='attach':
            for k in ('bvid','ref','file'):p.add_argument('--'+k,required=True)
            p.add_argument('--kind',choices=sorted(BODY|{'duplicate','comment','metadata'}),required=True)
            p.add_argument('--label')
        if cmd=='merge':p.add_argument('--batch')
        if cmd=='batch':p.add_argument('--limit',type=int,default=20)
        if cmd=='import-decisions':p.add_argument('--replace',action='store_true')
        if cmd=='export':
            p.add_argument('--urls',required=True);p.add_argument('--as-of')
    a=cli.parse_args()
    if a.cmd=='inventory':result=inventory(a)
    elif a.cmd=='subtitle':result=subtitle(a)
    else:
        folder=Path(a.run);folder.mkdir(parents=True,exist_ok=True)
        with (folder/'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);result=execute(a)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as error:
        sys.exit(str(error))

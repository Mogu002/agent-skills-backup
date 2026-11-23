const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const api = require('../scripts/chrome_evidence.js');
const url = 'https://tenant.feishu.cn/base/Example?table=tblExample';
const req = {kind:'field_detail', expectedUrl:url, identityConfirmed:true,
  object:'tblExample / Example', scopeSelector:'.active-panel', expectedText:'Example'};
function el(text='Example', attrs={}, children=[]) {
  return {id:'',tagName:'DIV',type:'',innerText:text,textContent:text,parentElement:null,
    getAttribute:k=>attrs[k]??null, classList:{contains:c=>(attrs.class||'').split(' ').includes(c)},
    getClientRects:()=>[{}],getBoundingClientRect:()=>({x:0,y:0,width:100,height:100}),
    querySelectorAll:()=>children, querySelector:()=>null, closest:()=>null};
}
function fixture(rows=[el()], text='Example') {
  const calls=[];
  const sandbox = vm.createContext({getComputedStyle:e=>e.style||{display:'block',visibility:'visible'}});
  const loc = {count:async()=>1,isVisible:async()=>true,innerText:async()=>text,
    locator:()=>loc, getByText:()=>loc, getByRole:()=>loc,filter:()=>loc,and:()=>loc,
    click:async()=>calls.push('click'),
    evaluateAll:async(fn,kind)=>{sandbox.rows=rows;sandbox.kind=kind;
      return JSON.parse(JSON.stringify(vm.runInContext('('+fn.toString()+')(rows,kind)',sandbox)));}};
  const tab = {url:async()=>url,playwright:{locator:()=>loc,getByText:()=>loc,getByRole:()=>loc,
    domSnapshot:async()=>'snapshot'}};
  return {tab,loc,calls};
}
test('captured panel is scoped, partial and never a score',async()=>{
  const f=fixture(); const out=await api.collect(f.tab,req);
  assert.equal(out.status,'partial');assert.equal(out.captureStatus,'captured');
  assert.equal(out.data[0].text,'Example');assert.equal(out.human_eval_fields,undefined);
  assert.ok(out.evidenceGaps.some(g=>g.code==='formula_results'));assert.deepEqual(f.calls,[]);
});
test('unknown identity, foreign host and URL drift reject before clicking',async()=>{
  for(const patch of [{identityConfirmed:false},{expectedUrl:'https://feishu.cn.evil.test/base/X'},
    {expectedUrl:'https://tenant.feishu.cn/base/Other'},{expectedUrl:'https://u:p@tenant.feishu.cn/base/X'}]) {
    const f=fixture();await assert.rejects(api.collect(f.tab,{...req,...patch}));assert.deepEqual(f.calls,[]);
  }
});
test('whole-page scopes, ambiguous and hidden targets reject',async()=>{
  for(const scopeSelector of ['body','html','*','div, body']) await assert.rejects(api.collect(fixture().tab,{...req,scopeSelector}));
  const f=fixture();f.loc.count=async()=>2;await assert.rejects(api.collect(f.tab,req));
  f.loc.count=async()=>1;f.loc.isVisible=async()=>false;await assert.rejects(api.collect(f.tab,req));
});
test('stale text and loading states reject',async()=>{
  await assert.rejects(api.collect(fixture([], 'Different').tab,req));
  await assert.rejects(api.collect(fixture([], 'Example 加载中...').tab,req));
});
test('empty and hidden DOM are missing evidence, not missing product',async()=>{
  const hidden=el();hidden.style={display:'none'};
  const out=await api.collect(fixture([hidden]).tab,req);
  assert.equal(out.captureStatus,'empty');assert.ok(out.evidenceGaps.some(g=>g.code==='empty_scope'));
});
test('inventory extracts IDs and excludes hidden retained nodes',async()=>{
  const visible=el('Example');visible.id='bitable-ssr-sidebar-item-tblExample';
  const hidden=el('Stale');hidden.style={visibility:'hidden'};
  const out=await api.collect(fixture([visible,hidden]).tab,{...req,kind:'inventory'});
  assert.deepEqual(out.data,[{id:'tblExample',name:'Example'}]);
});
test('switch unknown/true/false/mixed and disabled stay distinct',async()=>{
  const root=el();const nodes=[el('',{role:'switch'}),el('',{role:'switch',class:'ud__switch ud__switch-checked'}),
    el('',{role:'switch',class:'ud__switch'}),el('',{role:'checkbox','aria-checked':'mixed','aria-disabled':'true'})];
  nodes.forEach(n=>n.parentElement=root);root.querySelectorAll=s=>s.startsWith('input')?nodes:[];
  const out=await api.collect(fixture([root]).tab,req);
  assert.deepEqual(out.data[0].controls.map(c=>c.checked),[null,true,false,'mixed']);
  assert.equal(out.data[0].controls[3].disabled,true);
});
test('all supported actions are navigation only; dangerous action names rejected',async()=>{
  for(const action of ['save','publish','fill','check','submit','run','delete','click','fetch']) {
    const f=fixture();await assert.rejects(api.open(f.tab,{...req,action}));assert.deepEqual(f.calls,[]);
  }
  const f=fixture();const out=await api.open(f.tab,{...req,action:'fields'});
  assert.deepEqual(f.calls,['click']);assert.equal(out.snapshot,'snapshot');
});
test('object and chart selectors cannot be injected',async()=>{
  for(const action of ['object','chart_menu']) await assert.rejects(api.open(fixture().tab,{...req,action,id:'x"],button'}));
});
test('control loss propagates without retry or cleanup clicks',async()=>{
  const f=fixture();f.loc.click=async()=>{f.calls.push('click');throw new Error('control lost');};
  await assert.rejects(api.open(f.tab,{...req,action:'fields'}),/control lost/);assert.equal(f.calls.length,1);
});
test('capability gate rejects unknown, unavailable and wrong-object evidence',async()=>{
  const e=await api.collect(fixture().tab,req);
  const required=capability=>[{object:req.object,kind:req.kind,capability}];
  assert.equal(api.reviewCoverage([e],required('field_panel')).status,'needs_semantic_review');
  for(const cap of ['all_records','formula_results','invented_capability']) {
    const result=api.reviewCoverage([e],required(cap));assert.equal(result.missing.length,1);assert.equal(result.mayAutoScore,false);
  }
  assert.equal(api.reviewCoverage([e],[{...required('field_panel')[0],object:'other'}]).missing.length,1);
  assert.throws(()=>api.reviewCoverage([e],[]));assert.throws(()=>api.reviewCoverage([e],[{}]));
});
test('script has no browser side-channel or mutating API calls',()=>{
  const code=fs.readFileSync(require.resolve('../scripts/chrome_evidence.js'),'utf8');
  assert.doesNotMatch(code,/\.(fill|check|uncheck|setChecked|selectOption|fetch|cdp|goto|reload)\s*\(/);
  assert.doesNotMatch(code,/document\.cookie|localStorage|bitableStore|dashboardModel|require\(|import\(/);
});
test('permission column label uses its observed wrapper, not global index',async()=>{
  const root=el();const checkbox=el('',{role:'checkbox','aria-checked':'true'});
  checkbox.parentElement=root;checkbox.closest=s=>s.includes('checkbox-wrapper')?
    {querySelector:()=>({textContent:'可编辑'})}:null;
  root.querySelectorAll=s=>s.startsWith('input')?[checkbox]:[];
  const out=await api.collect(fixture([root]).tab,{...req,kind:'permission'});
  assert.equal(out.data[0].controls[0].label,'可编辑');assert.equal(out.data[0].controls[0].checked,true);
});
test('permission target is constrained to role/table menu nodes',async()=>{
  const f=fixture();let selected;
  f.loc.locator=s=>{selected=s;return f.loc;};
  await api.open(f.tab,{...req,action:'permission_target',name:'Role'});
  assert.equal(selected,'.bitable-perm-v2-role-menu-text-name, .base-perm__block-menu-item__start__title');
});
test('Form questions retain DOM identity, order, star, options without schema claims',async()=>{
  const root=el(),card=el();card.id='field-item-example';
  card.querySelector=s=>s.includes('title_wrapper')?el('Question',{class:'title Select'}):
    s.includes('number_content')?el('1'):s.includes('value_wrapper')?el('Option A\nOption B'):null;
  card.querySelectorAll=s=>s.includes('red_star')?[el('*')]:[];
  root.querySelectorAll=s=>s.includes('card_item')?[card]:[];
  const out=await api.collect(fixture([root]).tab,{...req,kind:'form'});
  assert.equal(out.data[0].questions[0].requiredMarker,true);
  assert.equal(out.data[0].questions[0].domId,'field-item-example');
  assert.equal(out.data[0].questions[0].title,'Question');
  assert.ok(out.evidenceGaps.some(g=>g.code==='source_field_types'));
});

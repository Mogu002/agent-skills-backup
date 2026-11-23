import {selectLoadedIds,selectionState} from './browser-state.mjs';
const markChooser=()=>{for(const e of document.querySelectorAll('[data-douyin-chooser]'))e.removeAttribute('data-douyin-chooser');const h=[...document.querySelectorAll('h1')].find(n=>n.textContent==='收藏视频到'&&n.getClientRects().length>0);if(!h)throw Error('Visible folder chooser absent');h.closest('.TIxHFAzq').setAttribute('data-douyin-chooser','true');};
const getRows=()=>[...document.querySelectorAll('[data-douyin-chooser] .PL6IqKFH')].map((n,i)=>({index:i,name:n.querySelector('.Z237Vhoq')?.textContent,checked:n.querySelector('input')?.getAttribute('aria-checked')==='true',count:Number(n.querySelector('.fB79ZcH0')?.textContent),private:!!n.querySelector('svg.Uu96uZsg')}));
export async function organizeBatch(page,category,ids,options={}){
 if(!ids.length)throw Error('Empty batch');
 await page.click('text="批量管理"',{label:'批量选择待归档收藏'});
 await page.evaluate(selectLoadedIds,ids);
 await page.waitForFunction(new Function('n',`return (${selectionState.toString()})()?.count===n;`),ids.length);
 const selected=await page.evaluate(selectionState);
 if(selected.ids.length!==ids.length||selected.ids.some(x=>!ids.includes(x)))throw Error('UI selection differs from planned ids');
 await page.click('text="加入收藏夹"',{label:'选择分类归档收藏夹'});
 await page.waitForSelector('h1:text-is("收藏视频到")',{state:'visible'});
 await page.evaluate(markChooser);
 let rows=await page.evaluate(getRows);
 // The folder chooser loads twenty rows per page. Exhaust it before creating a folder.
 if(!rows.some(r=>r.name===category))for(let stable=0;stable<2;){const count=rows.length;await page.evaluate(()=>{const e=document.querySelector('[data-douyin-chooser] .VNGTdslb');e.scrollTop=e.scrollHeight;});try{await page.waitForFunction(n=>document.querySelectorAll('[data-douyin-chooser] .PL6IqKFH').length>n,count,{timeout:2500});}catch{}rows=await page.evaluate(getRows);stable=rows.length===count?stable+1:0;}
 if(rows.filter(r=>r.name===category).length>1)throw Error('Ambiguous duplicate folder names; resolve by observed folder identity before submitting');
 let row=rows.find(x=>x.name===category);
 let created=false;
 if(!row&&options.knownFolderNames?.includes(category))throw Error('Known folder not loaded; refuse to create a duplicate');
 if(!row){
  await page.click('loc=role:button[name="新建收藏夹"]',{label:'新建所需主题收藏夹'});
  await page.fill('input[placeholder="请输入收藏夹的名称（15个字以内）"]',category);
  const isPublic=await page.evaluate(()=>document.querySelector('[role=switch]')?.getAttribute('aria-checked'));
  if(isPublic==='true')await page.click('[role="switch"]',{label:'设为私密收藏夹'});
  if(await page.evaluate(()=>document.querySelector('[role=switch]')?.getAttribute('aria-checked'))!=='false')throw Error('Private visibility not confirmed');
  await page.click('loc=role:button[name="确认"]',{label:'保存私密主题收藏夹'});
  await page.waitForSelector('h1:text-is("收藏视频到")',{state:'visible'});
 await page.evaluate(markChooser);
  rows=await page.evaluate(getRows);row=rows.find(x=>x.name===category);created=true;
 }
 if(!row)throw Error('Target folder absent after creation');
 if(!row.private&&!options.allowPublic)throw Error('Target folder is public; use a private destination unless explicitly authorized');
 for(const r of rows.filter(r=>r.checked&&r.name!==category))await page.click(`[data-douyin-chooser] .PL6IqKFH:nth-child(${r.index+1}) .semi-checkbox`,{label:'核对唯一归档目标'});
 if(!row.checked)await page.click(`[data-douyin-chooser] .PL6IqKFH:nth-child(${row.index+1}) .semi-checkbox`,{label:'选中目标主题收藏夹'});
 const checked=(await page.evaluate(getRows)).filter(r=>r.checked);
 if(checked.length!==1||checked[0].name!==category)throw Error('Multiple or wrong target folders selected');
 await page.click('loc=role:button[name="确定"]',{label:'保存本批收藏归档'});
 await page.waitForSelector('text="批量管理"',{state:'visible'});
 return {category,ids,count:ids.length,created,previousCount:row.count};
}

export function readState(){
 const root=document.querySelector('.route-scroll-container')||document;
 const anchors=[...root.querySelectorAll('li a[href^="/video/"],li a[href^="/note/"]')];
 const linkById=new Map(anchors.map(a=>[a.getAttribute('href')?.split('/').pop(),a.href]));
 let data=[];
 const list=root.querySelector('ul[data-e2e="scroll-list"]');
 const currentProps=list?.[Object.keys(list).find(k=>k.startsWith('__reactProps'))];
 if(currentProps){const children=Array.isArray(currentProps.children)?currentProps.children.flat(Infinity):[currentProps.children];data=children.filter(x=>x?.props?.itemInfo).map(x=>x.props.itemInfo);}
 let hasMore,statusCode;
 if(list){let f=list[Object.keys(list).find(k=>k.startsWith('__reactFiber'))];for(;f;f=f.return){const r=f.ref?.current;if(r?.getDataList&&r?.getHasMore){data=r.getDataList();hasMore=r.getHasMore();statusCode=r.getStatusCode?.();break;}}}
 if(!data.length)for(const n of anchors){let f=n[Object.keys(n).find(k=>k.startsWith('__reactFiber'))];for(;f;f=f.return){if(Array.isArray(f.memoizedProps)&&f.memoizedProps[0]?.props?.itemInfo){data=f.memoizedProps.map(x=>x.props.itemInfo);break;}}if(data.length)break;}

 const folders=[];const sidebar=document.querySelector('#collection-navigation');
 if(sidebar){for(const n of sidebar.querySelectorAll('p')){let f=n[Object.keys(n).find(k=>k.startsWith('__reactFiber'))];for(let i=0;f&&i<24;i++,f=f.return){const p=f.memoizedProps;if(p?.id&&typeof p.name==='string'&&typeof p.total==='number'){if(!folders.some(x=>x.id===p.id)){const row=n.closest('.yKNs6LhU');const total=row?.querySelector('.ICHy1sDK')?.textContent;folders.push({id:p.id,name:p.name,total:total==null?p.total:Number(total),active:row?row.classList.contains('rsXcs5vD'):p.active,secret:p.secret});}break;}}}}

 const route=document.querySelector('.route-scroll-container');
 return {data:[...new Map(data.map(j=>[j.awemeId,j])).values()].map(j=>({id:j.awemeId,url:linkById.get(j.awemeId)||(j.shareInfo?.shareUrl?(()=>{try{const u=new URL(j.shareInfo.shareUrl);return u.origin+u.pathname;}catch{return undefined;}})():undefined),desc:j.desc,author:j.authorInfo?.nickname,type:j.awemeType,tags:j.videoTag?.map(t=>t.tagName),title:j.itemTitle})),folders,noMore:(statusCode===0&&hasMore!==undefined&&!hasMore)||!!route?.textContent.includes('暂时没有更多了'),scroll:route?{top:route.scrollTop,height:route.scrollHeight,client:route.clientHeight}:null};
}
export function scrollBottom(){const e=document.querySelector('.route-scroll-container');e.scrollTop=e.scrollHeight;return true;}
export function readProgress(){
 const root=document.querySelector('.route-scroll-container')||document;
 const n=root.querySelector('li a[href^="/video/"],li a[href^="/note/"]');
 let count=0;
 const list=root.querySelector('ul[data-e2e="scroll-list"]');const p=list?.[Object.keys(list).find(k=>k.startsWith('__reactProps'))];
 if(p){const children=Array.isArray(p.children)?p.children.flat(Infinity):[p.children];count=children.filter(x=>x?.props?.itemInfo).length;}
 if(!count&&n){let f=n[Object.keys(n).find(k=>k.startsWith('__reactFiber'))];for(;f;f=f.return){if(Array.isArray(f.memoizedProps)&&f.memoizedProps[0]?.props?.itemInfo){count=f.memoizedProps.length;break;}}}

 let hasMore,statusCode;
 if(list){let f=list[Object.keys(list).find(k=>k.startsWith('__reactFiber'))];for(;f;f=f.return){const r=f.ref?.current;if(r?.getDataList&&r?.getHasMore){count=r.getDataList().length;hasMore=r.getHasMore();statusCode=r.getStatusCode?.();break;}}}
 return {count,hasMore,statusCode,noMore:(statusCode===0&&hasMore!==undefined&&!hasMore)||(root.textContent||'').includes('暂时没有更多了')};
}
export function selectionState(){
 const n=document.querySelector('.route-scroll-container li a');if(!n)return null;
 let f=n[Object.keys(n).find(k=>k.startsWith('__reactFiber'))];
 for(;f;f=f.return){const v=f.memoizedProps?.value;if(v?.changeSelectedItems)return {enabled:v.isListSelectable,count:v.selectedCount,max:v.maxSelectedCount,ids:v.selectItems.map(x=>x.awemeId)};}
 return null;
}
export function selectLoadedIds(ids){
 const n=document.querySelector('.route-scroll-container li a');if(!n)throw Error('No rendered collection list');
 let f=n[Object.keys(n).find(k=>k.startsWith('__reactFiber'))],records,context;
 for(;f;f=f.return){const p=f.memoizedProps;if(Array.isArray(p)&&p[0]?.props?.itemInfo)records=p.map(x=>x.props.itemInfo);if(p?.value?.changeSelectedItems)context=p.value;}
 if(!context?.isListSelectable||!records)throw Error('Selection contract missing');
 if(ids.length>context.maxSelectedCount||new Set(ids).size!==ids.length)throw Error('Invalid batch size or duplicate ids');
 const list=document.querySelector('.route-scroll-container ul[data-e2e="scroll-list"]');const p=list?.[Object.keys(list).find(k=>k.startsWith('__reactProps'))];if(p){const children=Array.isArray(p.children)?p.children.flat(Infinity):[p.children];const current=children.filter(x=>x?.props?.itemInfo).map(x=>x.props.itemInfo);if(current.length)records=current;}
 const lookup=new Map(records.map(x=>[x.awemeId,x]));if(ids.some(id=>!lookup.has(id)))throw Error('Requested ids absent from loaded list');
 context.changeSelectedItems(ids.map(id=>lookup.get(id)));
 return {requested:ids.length};
}

export async function loadNextPage(){
 const n=document.querySelector('.route-scroll-container ul[data-e2e="scroll-list"]');if(!n)throw Error('Rendered list absent');
 let f=n[Object.keys(n).find(k=>k.startsWith('__reactFiber'))];for(;f;f=f.return){const r=f.ref?.current;if(r?.getHasMore&&r?.getDataList&&r?.loadMoreData){if(!r.getHasMore())return{statusCode:r.getStatusCode?.(),hasMore:false};const out=await r.loadMoreData();return{statusCode:out?.statusCode,hasMore:out?.hasMore,received:out?.data?.length};}}
 throw Error('Verified list paging contract unavailable');
}

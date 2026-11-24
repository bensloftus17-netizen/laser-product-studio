/* V85 sales assistant: bounded text only, no artwork downloads. */
(() => {
 'use strict';
 const get=id=>document.getElementById(id);
 const button=get('salesBuild'),out=get('salesOutput'),status=get('salesStatus'),copy=get('salesCopy');
 if(!button||!out)return;
 let briefing='';
 function section(title,items){
  const box=document.createElement('section');
  const h=document.createElement('h3');h.textContent=title;box.append(h);
  for(const item of items){
   const p=document.createElement('p');p.textContent=item;box.append(p);
  }
  box.style.margin='16px 0';out.append(box);
 }
 function clear(){out.replaceChildren();out.hidden=true;copy.hidden=true;briefing='';}
 get('salesPart').addEventListener('input',clear);
 get('salesAudience').addEventListener('change',clear);
 button.addEventListener('click',async()=>{
  if(button.disabled)return;
  const part=(get('salesPart').value.trim()||get('part').value.trim()).toUpperCase();
  const audience=get('salesAudience').value;
  if(!/^[A-Z0-9.-]{3,16}$/.test(part)){status.textContent='Enter a valid Laser part number.';return;}
  get('salesPart').value=part;clear();button.disabled=true;
  status.textContent='Retrieving verified product facts and preparing sales guidance…';
  try{
   const response=await fetch('/api/sales-assistant/'+encodeURIComponent(part),{
    method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},
    body:JSON.stringify({audience})
   });
   const data=await readApiJson(response);
   if(get('salesPart').value.trim().toUpperCase()!==part||get('salesAudience').value!==audience){
    status.textContent='Selection changed. Build a briefing for the current selection.';return;
   }
   const groups=[
    ['Product and pricing',[data.title+' · Part '+data.part,data.price,data.price_status]],
    ['Target customer',[data.target_customer,data.category,data.focus]],
    ['Opening sales pitch',[data.pitch]],
    ['Verified selling points',data.selling_points.length?data.selling_points:['No concise verified features available. Consult the official source.']],
    ['Questions to ask',data.questions],
    ['Customer objections',data.objections.flatMap(x=>[x.objection,x.response])],
    ['Closing pitch',[data.closing]]
   ];
   for(const [title,items] of groups)section(title,items);
   if(typeof data.source==='string'&&/^https:\/\//.test(data.source)){
    const a=document.createElement('a');a.href=data.source;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Official product source';out.append(a);
   }
   briefing=groups.map(([title,items])=>title+'\n'+items.join('\n')).join('\n\n')+'\n\nOfficial source: '+(data.source||'Unavailable')+'\nInternal draft — verify before quoting.';
   out.hidden=false;copy.hidden=false;
   status.textContent=(data.method==='gemini-assisted'?'AI-assisted evidence selection.':'Verified-source fallback (AI unavailable or not configured).')+' Review all details before quoting.';
  }catch(error){status.textContent=error.message||'Sales briefing could not be created.';}
  finally{button.disabled=false;}
 });
 copy.addEventListener('click',async()=>{
  if(!briefing)return;
  try{await navigator.clipboard.writeText(briefing);status.textContent='Sales briefing copied.';}
  catch{status.textContent='Clipboard unavailable; select and copy the displayed text.';}
 });
})();

(() => {
 'use strict';
 const get=id=>document.getElementById(id);
 const form=get('salesForm'),button=get('salesBuild'),out=get('salesOutput'),status=get('salesStatus');
 if(!form||!button||!out)return;
 function element(tag,text,className){
  const node=document.createElement(tag);
  if(text)node.textContent=text;
  if(className)node.className=className;
  return node;
 }
 function list(items,ordered=false){
  const node=element(ordered?'ol':'ul');
  for(const item of items)node.append(element('li',item));
  return node;
 }
 function details(label,content){
  const node=element('details',null,'sales-detail');
  node.append(element('summary',label),content);
  return node;
 }
 function render(data){
  const points=data.selling_points;
  const steps=[...new Set(data.demonstration_plan?.length?data.demonstration_plan:[data.closing])];
  const header=element('header',null,'sales-brief-header');
  const identification=element('div');
  identification.append(element('p','Laser '+data.part+' · '+data.audience,'sales-meta'),
                        element('h3',data.title),
                        element('p',data.price,'sales-price'),
                        element('p',data.price_status,'sales-meta'));
  const actions=element('div',null,'sales-brief-actions');
  const copy=element('button','Copy briefing','secondary');
  copy.type='button';
  copy.id='salesCopy';
  actions.append(copy);
  if(typeof data.source==='string'&&/^https:\/\//.test(data.source)){
   const source=element('a','Official product page');
   source.href=data.source;source.target='_blank';source.rel='noopener noreferrer';
   actions.append(source);
  }
  header.append(identification,actions);

  const opening=element('section',null,'sales-opening');
  opening.append(element('h4','Start the conversation'),element('p',data.pitch));
  const facts=element('section',null,'sales-facts');
  facts.append(element('h4','Verified selling points'),
               points.length?list(points):element('p','See the official product page for specifications.'));
  const primary=element('div',null,'sales-brief-main');
  primary.append(opening,facts);
  const replies=element('dl');
  for(const objection of data.objections){
   replies.append(element('dt',objection.objection),element('dd',objection.response));
  }
  const followup=element('div',null,'sales-followup');
  followup.append(details('Questions to ask',list([...new Set(data.questions)])),
                  details('Handling objections',replies),
                  details('Demonstration and next steps',list(steps,true)));
  out.replaceChildren(header,primary,followup);

  const briefing=[
   data.title+' · Laser '+data.part,data.audience,data.price,data.price_status,data.focus,
   'Opening pitch\n'+data.pitch,
   'Verified selling points\n'+points.join('\n'),
   'Questions to ask\n'+[...new Set(data.questions)].join('\n'),
   'Handling objections\n'+data.objections.map(item=>item.objection+'\n'+item.response).join('\n\n'),
   'Demonstration and next steps\n'+steps.join('\n'),
   'Official source: '+(data.source||'Unavailable'),'Internal draft — verify before quoting.'
  ].filter(Boolean).join('\n\n');
  copy.addEventListener('click',async()=>{
   try{await navigator.clipboard.writeText(briefing);status.textContent='Sales briefing copied.';}
   catch{status.textContent='Clipboard unavailable. Open the sections you need and copy the text.';}
  });
 }
 function clear(){
  out.replaceChildren();out.hidden=true;status.textContent='';
 }
 get('salesPart').addEventListener('input',clear);
 get('salesAudience').addEventListener('change',clear);
 get('salesOfficialUrl').addEventListener('input',clear);
 form.addEventListener('submit',async(event)=>{
  event.preventDefault();
  if(button.disabled)return;
  const part=(get('salesPart').value.trim()||get('part').value.trim()).toUpperCase();
  const audience=get('salesAudience').value;
  const official_url=get('salesOfficialUrl').value.trim();
  if(!/^[A-Z0-9.-]{3,16}$/.test(part)){status.textContent='Enter a valid Laser part number.';return;}
  get('salesPart').value=part;clear();button.disabled=true;
  status.textContent='Preparing briefing…';
  try{
   const response=await fetch('/api/sales-assistant/'+encodeURIComponent(part),{
    method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},
    body:JSON.stringify(official_url?{audience,official_url}:{audience})
   });
   const data=await readApiJson(response);
   if(get('salesPart').value.trim().toUpperCase()!==part||get('salesAudience').value!==audience||get('salesOfficialUrl').value.trim()!==official_url)return;
   render(data);
   out.hidden=false;
   status.textContent='Briefing ready. Review before quoting.';
  }catch(error){status.textContent=error.message||'Sales briefing could not be created.';}
  finally{button.disabled=false;}
 });
})();

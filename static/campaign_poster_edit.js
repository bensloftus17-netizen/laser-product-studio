/* V80 — verified manufacturer photo picker and targeted campaign editor.
 * Browser controls never fetch image-processing AI, unapproved photo URLs or
 * change official claims. Only one poster is re-rendered on Save.
 */
(() => {
  'use strict';
  const ids={poster_technical:0,poster_price:1,poster_smart:2};
  const get=id=>document.getElementById(id);
  const panel=get('campaignPosterEditor'),gallery=get('campaignAssets');
  if(!panel||!gallery)return;
  let selected=null;
  const setStatus=message=>{get('posterEditStatus').textContent=message;};
  function selectedPhotoIndex(){
    const checked=get('posterEditPhotoPicker').querySelector('input[name="poster_source_photo"]:checked');
    return checked?Number(checked.value):null;
  }
  function buildPhotoPicker(manifest,token,assetId){
    const root=get('posterEditPhotoPicker');
    root.replaceChildren();
    const options=(manifest.poster_photo_choices||[]).slice(0,4);
    const current=manifest.artwork_photo_sources?.[assetId]?.sha256;
    if(!options.length){
      const notice=document.createElement('small');
      notice.textContent='Only the current approved product photograph is available.';
      root.append(notice);
      return;
    }
    let defaultIndex=options.findIndex(row=>row.sha256===current);
    if(defaultIndex<0)defaultIndex=0;
    for(const entry of options){
      if(!Number.isInteger(entry.index)||entry.index<0||entry.index>=4)continue;
      const label=document.createElement('label');
      label.className='poster-photo-option';
      label.title=entry.source_url||'Manufacturer source photograph';
      const radio=document.createElement('input');
      radio.type='radio';radio.name='poster_source_photo';
      radio.value=String(entry.index);
      radio.checked=entry.index===defaultIndex;
      const picture=document.createElement('img');
      picture.loading='lazy';picture.decoding='async';
      picture.alt='Official Laser photo option '+(entry.index+1);
      picture.src='/api/campaign/photos/'+encodeURIComponent(token)+'/'+entry.index;
      const text=document.createElement('small');
      text.textContent=entry.index===0?'Main product photo':
        (entry.type||'Alternate view')+' '+(entry.index+1);
      label.append(radio,picture,text);
      root.append(label);
    }
  }
  function open(id){
    if(!campaignData||!Object.prototype.hasOwnProperty.call(ids,id))return;
    const manifest=campaignData.manifest,token=campaignData.token;
    const angle=manifest.angles?.[ids[id]];
    if(!angle)return;
    const features=manifest.poster_editor?.verified_features||[];
    selected=id;
    get('posterEditTitle').textContent='Edit '+angle.name;
    get('posterEditHeadline').value=angle.headline||manifest.title;
    const menu=get('posterEditFeature');
    menu.replaceChildren();
    const none=document.createElement('option');
    none.value='-1';none.textContent='No featured fact';menu.append(none);
    features.forEach((fact,index)=>{
      const option=document.createElement('option');
      option.value=String(index);option.textContent=fact;menu.append(option);
    });
    menu.value=String(features.indexOf(angle.selling_point));
    const layoutLabels={
      poster_technical:['Technical datasheet','Alternative technical','Compact technical'],
      poster_price:['Bold promotion','Price spotlight','Product hero'],
      poster_smart:['Editorial spotlight','Workshop focus','Benefit-led layout'],
    };
    [...get('posterEditVariant').options].forEach((option,index)=>{
      option.textContent=layoutLabels[id][index]||('Layout '+(index+1));
    });
    get('posterEditVariant').value=String(
      angle.layout_variant??manifest.artwork_quality?.[id]?.variation??0);
    const direction=manifest.creative_plan?.creative_decisions?.[ids[id]]?.art_direction||{};
    const priceVisible=id==='poster_price' &&
      manifest.promo_template!=='workshop_showcase';
    get('posterEditPriceOptions').hidden=!priceVisible;
    if(priceVisible){
      const preferred=String(angle.price_style||direction.price_style||'panel');
      get('posterEditPriceStyle').value=
        [...get('posterEditPriceStyle').options].some(x=>x.value===preferred)?
          preferred:'panel';
      const size=String(angle.headline_size||direction.headline_size||'normal');
      get('posterEditHeadlineSize').value=['small','normal','large'].includes(size)?
        size:'normal';
    }
    buildPhotoPicker(manifest,token,id);
    const image=get('posterEditPreview');
    const card=gallery.querySelector('[data-asset-card="'+id+'"]');
    image.src=card?.querySelector('img')?.src||'/api/campaign/assets/'+
      encodeURIComponent(token)+'/'+encodeURIComponent(id);
    setStatus('Choose a verified image, layout or fact, then update this poster.');
    panel.hidden=false;
    panel.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  gallery.addEventListener('click',event=>{
    const button=event.target.closest('button[data-edit-poster]');
    if(button)open(button.dataset.editPoster);
  });
  panel.addEventListener('click',event=>{
    const trigger=event.target.closest('button[data-editor-focus]');
    if(!trigger)return;
    const id=trigger.dataset.editorFocus,target=get(id);
    if(!target)return;
    target.scrollIntoView({behavior:'smooth',block:'center'});
    const focus=target.matches('input,select,textarea')?target:
      target.querySelector('input,select,textarea');
    if(focus)focus.focus({preventScroll:true});
  });
  get('posterEditClose').addEventListener('click',()=>{
    selected=null;panel.hidden=true;
    get('posterEditPreview').removeAttribute('src');
  });
  get('posterEditSave').addEventListener('click',async()=>{
    if(!campaignData||!selected)return;
    const assetId=selected,token=campaignData.token;
    const button=get('posterEditSave');
    button.disabled=true;
    setStatus('Verifying the manufacturer photo and reflowing this poster…');
    try{
      const edits={
        headline:get('posterEditHeadline').value,
        feature_index:Number(get('posterEditFeature').value),
        layout_variant:Number(get('posterEditVariant').value),
      };
      const chosen=selectedPhotoIndex();
      const candidate=(campaignData.manifest.poster_photo_choices||[])
        .find(item=>item.index===chosen);
      const currentHash=campaignData.manifest.artwork_photo_sources?.[assetId]?.sha256;
      // Re-selecting the current photo should not force an unnecessary
      // source decode/QA on the 512 MiB worker.
      if(chosen!==null && candidate && candidate.sha256!==currentHash){
        edits.photo_index=chosen;
      }
      if(assetId==='poster_price'&&
         campaignData.manifest.promo_template!=='workshop_showcase'){
        edits.price_style=get('posterEditPriceStyle').value;
        edits.headline_size=get('posterEditHeadlineSize').value;
      }
      const response=await fetch('/api/campaign/edit/'+
        encodeURIComponent(token)+'/'+encodeURIComponent(assetId),{
          method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify(edits),
        });
      const result=await response.json();
      if(!response.ok)throw Error(result.error||'Unable to edit poster.');
      const manifest=result.manifest;
      campaignData.manifest=manifest;
      const angle=manifest.angles[ids[assetId]];
      get('posterEditVariant').value=String(angle.layout_variant??edits.layout_variant);
      const box=get('campaignAngles').children[ids[assetId]];
      if(box){
        const heading=box.querySelector('b'),detail=box.querySelector('p');
        if(heading)heading.textContent=angle.headline;
        if(detail)detail.textContent=angle.selling_point;
      }
      const card=gallery.querySelector('[data-asset-card="'+assetId+'"]');
      const assetUrl='/api/campaign/assets/'+encodeURIComponent(token)+'/'+
                     encodeURIComponent(assetId);
      const updated=assetUrl+'?revision='+encodeURIComponent(result.revision);
      if(card){
        const img=card.querySelector('img'),openLink=card.querySelector('a[aria-label^="Open"]');
        const save=card.querySelector('.campaign-save-image');
        const share=card.querySelector('button.asset-share-button');
        if(img)img.src=updated;
        if(openLink)openLink.href=updated;
        if(save)save.href=updated+'&download=1';
        if(share){
          preparedShareFiles.delete(share);
          delete share.dataset.shareLoading;
          share.dataset.shareUrl=updated;
          prepareShareButton(share);
        }
      }
      get('posterEditPreview').src=updated;
      // Invalidate any old per-tab copy of this PNG so reopening the editor
      // doesn't resurrect a previous revision after Render restarts.
      if(typeof campaignLocalPNGs!=='undefined'&&campaignLocalPNGs.has(assetId)){
        const stale=campaignLocalPNGs.get(assetId);
        if(typeof stale==='string'&&stale.startsWith('blob:'))URL.revokeObjectURL(stale);
        campaignLocalPNGs.delete(assetId);
      }
      const zip=get('campaignShareZip');
      if(zip){
        preparedShareFiles.delete(zip);delete zip.dataset.shareLoading;
        prepareShareButton(zip);
      }
      const repaired=result.quality?.auto_repaired;
      setStatus((repaired?'Layout automatically adjusted to keep all text readable. ':'')+
        'Updated this poster and the campaign ZIP. The other eight graphics and copy drafts are unchanged.');
    }catch(error){
      setStatus(error.message||'Poster could not be updated. Your original remains unchanged.');
    }finally{
      button.disabled=false;
    }
  });
})();

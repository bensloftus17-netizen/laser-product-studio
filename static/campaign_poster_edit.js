/* Laser Product Studio V44: independently edit one source-verified poster.
   This is not a second generator. Gemini is never called from this editor. */
(() => {
  'use strict';
  const ids = {poster_technical:0,poster_price:1,poster_smart:2};
  const get = id => document.getElementById(id);
  const panel = get('campaignPosterEditor');
  const gallery = get('campaignAssets');
  if (!panel || !gallery) return;
  let selected = null;
  const setStatus = message => { get('posterEditStatus').textContent = message; };
  function open(id) {
    if (!campaignData || !Object.prototype.hasOwnProperty.call(ids,id)) return;
    const manifest = campaignData.manifest;
    const angle = manifest.angles[ids[id]];
    const features = manifest.poster_editor?.verified_features || [];
    selected = id;
    get('posterEditTitle').textContent = 'Edit ' + angle.name;
    get('posterEditHeadline').value = angle.headline || manifest.title;
    const menu = get('posterEditFeature');
    menu.replaceChildren();
    const none = document.createElement('option');
    none.value = '-1'; none.textContent = 'No featured fact'; menu.append(none);
    features.forEach((fact,index) => {
      const option=document.createElement('option');
      option.value=String(index);
      option.textContent=fact;menu.append(option);
    });
    menu.value = String(features.indexOf(angle.selling_point));
    get('posterEditVariant').value = String(
      angle.layout_variant ?? manifest.artwork_quality?.[id]?.variation ?? 0);
    setStatus('Changes update this poster without rebuilding the campaign.');
    panel.hidden = false;
    panel.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  gallery.addEventListener('click',event => {
    const button = event.target.closest('button[data-edit-poster]');
    if (button) open(button.dataset.editPoster);
  });
  get('posterEditClose').addEventListener('click',() => {
    selected = null;panel.hidden = true;
  });
  get('posterEditSave').addEventListener('click',async() => {
    if (!campaignData || !selected)return;
    const assetId=selected, token=campaignData.token;
    const button=get('posterEditSave');
    button.disabled=true;
    setStatus('Checking manufacturer facts and re-rendering this poster…');
    try {
      const response=await fetch('/api/campaign/edit/'+
          encodeURIComponent(token)+'/'+encodeURIComponent(assetId), {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          headline:get('posterEditHeadline').value,
          feature_index:Number(get('posterEditFeature').value),
          layout_variant:Number(get('posterEditVariant').value)
        })
      });
      // The same server replies with a structured error on rejection.
      const result=await response.json();
      if(!response.ok)throw Error(result.error || 'Unable to edit poster.');
      const manifest=result.manifest;
      campaignData.manifest=manifest;
      const angle=manifest.angles[ids[assetId]];
      const box=get('campaignAngles').children[ids[assetId]];
      if(box){
        const heading=box.querySelector('b');
        const detail=box.querySelector('p');
        if(heading)heading.textContent=angle.headline;
        if(detail)detail.textContent=angle.selling_point;
      }
      const card=Array.from(gallery.querySelectorAll('[data-asset-card]'))
        .find(node=>node.dataset.assetCard===assetId);
      if(card) {
        const assetUrl='/api/campaign/assets/'+encodeURIComponent(token)+'/'+
            encodeURIComponent(assetId);
        const newUrl=assetUrl+'?revision='+encodeURIComponent(result.revision);
        const img=card.querySelector('img');
        if(img)img.src=newUrl;
        const openLink=card.querySelector('a[aria-label^="Open"]');
        if(openLink)openLink.href=newUrl;
        const share=card.querySelector('button.asset-share-button');
        if(share) {
          preparedShareFiles.delete(share);
          delete share.dataset.shareLoading;
          share.dataset.shareUrl=newUrl;
          prepareShareButton(share);
        }
      }
      const shareZip=get('campaignShareZip');
      preparedShareFiles.delete(shareZip);
      delete shareZip.dataset.shareLoading;
      prepareShareButton(shareZip);
      setStatus('Poster updated. Your ZIP contains the new PNG and updated summary. Other posters and Copy Editor drafts are unchanged.');
    } catch(error) {
      setStatus(error.message || 'Poster could not be updated.');
    } finally {
      button.disabled=false;
    }
  });
})();

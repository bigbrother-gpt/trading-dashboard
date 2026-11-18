/* HERMES v1: safely display unverified source headlines from a static snapshot.
   No HTML interpolation of untrusted feed text; no fabricated geolocation. */
(async function(){
  const banner=document.querySelector('.notice');
  try {
    const response=await fetch('data/events.json',{cache:'no-store'});
    if(!response.ok)throw Error('No published snapshot');
    const payload=await response.json();
    if(payload.schema_version!==1||!Array.isArray(payload.items)||!payload.generated_at)throw Error('Invalid snapshot');
    const age=Date.now()-Date.parse(payload.generated_at);
    if(!Number.isFinite(age)||age< -3600000||age>48*3600000)throw Error('Snapshot stale');
    const entries=payload.items.slice(0,180);
    // Map country anchors are tentative headline mentions, never verified incident locations.
    data.splice(0,data.length);
    for(const e of entries){
      if(e.geo_precision==='country_label_anchor' && Array.isArray(e.coordinates) && e.coordinates.length===2 &&
        e.coordinates.every(Number.isFinite) && typeof e.country==='string'){
        data.push([e.country,e.coordinates[0],e.coordinates[1],3,0,String(e.title||''),
          'Unverified publisher headline. Country name explicitly mentioned; actual event location not confirmed.',
          'No verified financial impact.',Array.isArray(e.potential_instruments)?e.potential_instruments:[]]);
      }
    }
    render();
    const mapStatus=document.querySelector('#selection');
    mapStatus.textContent=`${data.length} tentative country markers from headlines (not verified event locations). Select a pin to inspect; see the news list for source evidence.`;
    banner.textContent=`LIVE FEED METADATA / UNVERIFIED HEADLINES · ${entries.length} ITEMS · UPDATED ${new Date(payload.generated_at).toISOString().slice(0,16)} UTC · ${payload.source_health?.ok??'?'} FEEDS REACHABLE`;
    banner.style.color='#d6ad64';
    const section=document.querySelector('#events');
    const selector=document.querySelector('#instrument');
    const clear=document.querySelector('#clear');
    const formatDate=s=>{if(!s)return 'Date unknown';const d=new Date(s);return Number.isFinite(d.getTime())?d.toISOString().slice(0,16).replace('T',' ')+' UTC':'Date unknown'};
    function renderLive(){
      section.replaceChildren();
      const filter=selector.value;
      const filtered=entries.filter(e=>(!filter||(Array.isArray(e.potential_instruments)&&e.potential_instruments.includes(filter)))&&(!country||e.country===country));
      const title=document.createElement('div');title.className='group';title.textContent=`UNVERIFIED SOURCE HEADLINES / ${filtered.length}`;section.append(title);
      const note=document.createElement('p');note.className='notice';note.textContent='Headlines supplied by external publishers. Relevance is rule-based and preliminary. No independent fact verification, importance ranking or market impact assessment has been performed. Country markers are tentative headline mentions only.';section.append(note);
      for(const item of filtered){
        const details=document.createElement('details');
        const summary=document.createElement('summary');summary.style.gridTemplateColumns='1fr auto';
        const headline=document.createElement('span');headline.className='headline';headline.textContent=String(item.title||'Untitled').slice(0,300);
        const when=document.createElement('span');when.className='mono';when.textContent=formatDate(item.published);
        summary.append(headline,when);details.append(summary);
        const body=document.createElement('div');body.className='body';
        const status=document.createElement('p');status.className='mono';status.textContent='UNVERIFIED · '+(item.triage==='candidate'?'POTENTIAL FINANCIAL RELEVANCE':'REVIEW / UNMATCHED');body.append(status);
        if(item.country){const place=document.createElement('p');place.textContent='Country mentioned: '+item.country+' (not verified event location)';body.append(place)}
        for(const claim of (Array.isArray(item.claims)?item.claims:[]).slice(0,3)){
          const cp=document.createElement('p');cp.textContent='Publisher assertion, NOT independently confirmed: '+String(claim.text||'').slice(0,300);body.append(cp)
        }
        const topics=document.createElement('p');topics.textContent='Topics: '+(Array.isArray(item.topics)&&item.topics.length?item.topics.join(' · '):'Not classified');body.append(topics);
        const assets=document.createElement('p');assets.textContent='Potentially related instruments (not a price prediction): '+(Array.isArray(item.potential_instruments)&&item.potential_instruments.length?item.potential_instruments.join(' · '):'Not established');body.append(assets);
        const sources=document.createElement('p');sources.textContent='Original sources: ';body.append(sources);
        for(const ref of (Array.isArray(item.references)?item.references:[]).slice(0,12)){
          try{const url=new URL(ref.url);if(!['https:','http:'].includes(url.protocol))continue;
            const a=document.createElement('a');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';a.textContent=String(ref.source||url.hostname).slice(0,100);body.append(a,document.createTextNode(' · '));
          }catch(_){}
        }
        details.append(body);section.append(details);
      }
      if(!filtered.length){const p=document.createElement('p');p.className='empty';p.textContent='No matching feed headlines.';section.append(p)}
    }
    // Replace the demo news renderer so map pin selection cannot resurrect fictional news.
    news=renderLive;
    selector.onchange=renderLive;
    clear.onclick=()=>{selector.value='';country='';selected=-1;document.querySelector('#selection').textContent='Country markers are tentative; choose a pin to filter.';renderLive()};
    renderLive();
  } catch(err){
    data.splice(0,data.length); render(); document.querySelector('#events').replaceChildren(); document.querySelector('#selection').textContent='No validated live snapshot. Map cleared to avoid displaying demonstration events.'; banner.textContent='NO VALIDATED LIVE SNAPSHOT — NEWS AND MAP DISABLED';
    banner.style.color='#d6ad64';
  }
})();

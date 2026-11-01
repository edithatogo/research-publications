// BrowserOS page.evaluate expressions for the public GrantConnect intake.
// Invoke on an owned www.grants.gov.au page. Inputs are selected register rows.
async function captureGrantConnectFeed() {
  const url = 'https://www.grants.gov.au/public_data/rss/rss.xml';
  if (location.origin !== new URL(url).origin) throw Error('Wrong browser origin');
  const response = await fetch(url, {credentials:'omit', cache:'no-store', redirect:'error', signal:AbortSignal.timeout(20000)});
  if (!response.ok) throw Error('Feed HTTP '+response.status);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes.length > 5000000) throw Error('Feed exceeds capture limit');
  const sha = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)), x=>x.toString(16).padStart(2,'0')).join('');
  window.gcBytes = bytes;
  return {url:response.url,status:response.status,headers:Object.fromEntries(response.headers),size:bytes.length,sha,utc:new Date().toISOString()};
}

async function captureGrantConnectPages(rows) {
  if (rows.length > 10) throw Error('At most ten official pages per batch');
  return Promise.all(rows.map(async row=>{
    const url = new URL(row.URL);
    if (url.origin !== 'https://www.grants.gov.au' || location.origin !== url.origin || url.pathname.toLowerCase() !== '/go/show')
      throw Error('Unexpected opportunity URL');
    const source={key:row.OpportunityKey,url:row.URL,at:new Date().toISOString()};
    try {
      const response=await fetch(url,{credentials:'omit',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000)});
      if(!response.ok)return {...source,status:response.status};
      const doc=new DOMParser().parseFromString(await response.text(),'text/html');
      const values=label=>Array.from(doc.querySelectorAll('.list-desc'))
        .filter(el=>el.querySelector(':scope > span')?.textContent.trim()===label)
        .map(el=>el.querySelector('.list-desc-inner')?.textContent.trim());
      return {...source,status:response.status,ids:values('GO ID:'),close:values('Close Date & Time:')};
    }catch(error){return {...source,error:String(error)};}
  }));
}

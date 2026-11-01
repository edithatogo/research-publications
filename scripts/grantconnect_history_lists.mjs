// Provision only the historical registers. Item writes belong to the ready flow.
import fs from 'node:fs';
import {target} from './bootstrap_outcome_register.mjs';

export async function provision({args,pin,auth,request}){
  const [site, journal]=args, root=target(pin,site);
  fs.mkdirSync(journal,{mode:0o700});
  const token=await auth.ensureAccessToken(new URL(site).origin,{log:async()=>{},logToStderr:async()=>{}},false);
  let sequence=0;
  const send=async(method,url,data,headers={})=>{
    const id=++sequence;
    fs.writeFileSync(journal+'/'+id+'-intent.json',JSON.stringify({method,url,data}),{flag:'wx'});
    const r=await request.req({method,url,data:data?JSON.stringify(data):undefined,timeout:30000,maxRedirects:0,
      headers:{Authorization:'Bearer '+token,Accept:'application/json;odata=verbose','Content-Type':'application/json;odata=verbose',...headers},responseType:'text'});
    return r.data?(JSON.parse(r.data).d??{}):{};
  };
  const result={};
  for(const [kind,name] of Object.entries({awards:'GrantConnect Historical Awards',closed:'GrantConnect Closed Opportunities',links:'GrantConnect Confirmed Award Links'})){
    const found=await send('GET',root+"?$select=Id,Title,EnableVersioning&$filter=Title eq '"+name+"'");
    if(found.results.length)throw Error('Existing history list: reconcile before bootstrap');
    const list=await send('POST',root,{__metadata:{type:'SP.List'},Title:name,BaseTemplate:100,EnableVersioning:true});
    const url=root+"(guid'"+list.Id+"')";
    for(const [field,type] of [['HistoryKey','Text'],['GAID','Text'],['GOID','Text'],['EvidenceHash','Text'],['SourceEvidence','Note']]){
      const unique=field==='HistoryKey'?' Indexed="TRUE" EnforceUniqueValues="TRUE" Required="TRUE"':'';
      await send('POST',url+'/fields/createfieldasxml',{parameters:{__metadata:{type:'SP.XmlSchemaFieldCreationInformation'},SchemaXml:'<Field Type="'+type+'" Name="'+field+'" StaticName="'+field+'" DisplayName="'+field+'"'+unique+' />',Options:0}});
    }
    const check=await send('GET',url+"/fields/getbyinternalnameortitle('HistoryKey')?$select=EnforceUniqueValues");
    if(check.EnforceUniqueValues!==true)throw Error('Unique HistoryKey required');
    result[kind]=list.Id;fs.writeFileSync(journal+'/lists.json',JSON.stringify(result));
  }
}

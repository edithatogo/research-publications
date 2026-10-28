// SPDX-License-Identifier: Apache-2.0
import fs from 'node:fs';
export async function acquireWorkloadLock(directory,{timeoutMs=30000,intervalMs=100}={}){
 if(!Number.isInteger(timeoutMs)||timeoutMs<0||timeoutMs>60000||!Number.isInteger(intervalMs)||intervalMs<1||intervalMs>1000)throw Error('Finite bounded lock wait required');
 const deadline=Date.now()+timeoutMs;
 while(true){
  try{fs.mkdirSync(directory);return;}
  catch(error){if(error.code!=='EEXIST')throw error;}
  if(Date.now()>=deadline)throw Error('Existing workload owner remains active; no authentication or native request started');
  await new Promise(resolve=>setTimeout(resolve,Math.min(intervalMs,Math.max(1,deadline-Date.now()))));
 }
}

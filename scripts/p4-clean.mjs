import {readFileSync} from 'node:fs';
const DEP='E:/CodexWorkspaces/artifacts/witnora/2026-09-10-stripe-governed';
const cfg=JSON.parse(readFileSync(DEP+'/gateway/gateway.json','utf8'));
const {gatewayToken}=JSON.parse(readFileSync(DEP+'/gateway/secrets.json','utf8'));
const gw=async(path,body)=>{const r=await fetch('http://127.0.0.1:'+cfg.port+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+gatewayToken,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return {status:r.status,value:await r.json().catch(()=>({}))};};
// A real DENIED action from the 2026-09-13 run
const denied='0f4285ac-b9d5-4400-bff4-7fd3aac9daf4';
const g=await gw('/v1/actions/'+denied+'/execution-grant',{grant:{payload:{executionGrantId:'clean-'+Date.now(),actionId:denied,allowedOperation:'REFUND',maxUses:1,notBefore:new Date().toISOString(),expiresAt:new Date(Date.now()+60000).toISOString()}},idempotencyKey:'p4clean-'+Date.now()});
console.log('grant on DENIED action ->',JSON.stringify({http:g.status,error:(g.value.error||JSON.stringify(g.value)).slice(0,160)}));
// verify the action is indeed terminal
const a=await gw('/v1/actions/'+denied);
console.log('action status ->',JSON.stringify({http:a.status,status:a.value.status,decision:a.value.decision}));

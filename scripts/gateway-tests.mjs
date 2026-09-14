import {readFileSync} from 'node:fs';
const OUT='E:/CodexWorkspaces/artifacts/witnora/2026-09-14-agent-isolation';
const DEP='E:/CodexWorkspaces/artifacts/witnora/2026-09-10-stripe-governed';
const cfg=JSON.parse(readFileSync(DEP+'/gateway/gateway.json','utf8'));
const {gatewayToken}=JSON.parse(readFileSync(DEP+'/gateway/secrets.json','utf8'));
const pay=JSON.parse(readFileSync(OUT+'/evidence/payment-A2.json','utf8'));
const gw=async(path,body,method)=>{const r=await fetch('http://127.0.0.1:'+cfg.port+path,{method:method||(body?'POST':'GET'),headers:{Authorization:'Bearer '+gatewayToken,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return {status:r.status,value:await r.json().catch(()=>({}))};};
const es={paymentIntentId:pay.paymentIntentId,amount:500,currency:'usd',status:'succeeded',livemode:false};
const mkProposal=(label,extra)=>({externalId:'iso-A2-'+label+'-'+Date.now(),agentId:cfg.agentIdentity.externalId,principal:{id:cfg.agentIdentity.externalId},actionType:'PAY',targetSystem:'StripeTestMode',requestedPermissions:[],amount:5,currency:'USD',expectedState:es,executionIntent:{adapterId:'witnora.stripe-test.refund.v1',adapterVersionConstraint:'1.0.0',allowedOrigins:['https://api.stripe.com'],allowedOperation:'REFUND',allowedResource:'payment-intents/'+pay.paymentIntentId,approvedParameters:{accountId:pay.accountId,paymentIntentId:pay.paymentIntentId,amount:500,currency:'usd'},outcomePredicate:{type:'expected_state_subset',expectedState:es},agentBuildId:'stripe-test-refund-agent-1.0.0',agentBuildDigest:'77bc1283621c3d326335b2f1537c542ab0ca547ba3d861b98ede7080517e542b'},...extra});

// (1) requireMandate:false
let p=mkProposal('nomandate',{requireMandate:false});
let r=await gw('/v1/actions',{proposal:p,idempotencyKey:p.externalId});
console.log('(1) requireMandate:false ->',JSON.stringify({http:r.status,status:r.value.status,decision:r.value.decision,reasons:r.value.reasons,id:r.value.id}));

// (2) no requireMandate field at all
p=mkProposal('bare',{});
r=await gw('/v1/actions',{proposal:p,idempotencyKey:p.externalId});
console.log('(2) no-mandate-field ->',JSON.stringify({http:r.status,status:r.value.status,decision:r.value.decision,reasons:r.value.reasons,id:r.value.id}));
const pendingId=(r.value.status==='PENDING_APPROVAL')?r.value.id:null;

// (3) clean gateway refusal: issue execution-grant for an unapproved action (well-formed-ish)
const someId=r.value.id||'00000000-0000-0000-0000-000000000000';
const g=await gw('/v1/actions/'+someId+'/execution-grant',{grant:{payload:{executionGrantId:'x',actionId:someId,allowedOperation:'REFUND',allowedResource:'payment-intents/'+pay.paymentIntentId,maxUses:1,notBefore:new Date().toISOString(),expiresAt:new Date(Date.now()+60000).toISOString()}},idempotencyKey:'iso-grant-'+Date.now()});
console.log('(3) execution-grant on unapproved action ->',JSON.stringify({http:g.status,error:(g.value.error||JSON.stringify(g.value)).slice(0,160)}));

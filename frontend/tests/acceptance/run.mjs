/** Browser acceptance for the actual single-chat React workspace and FastAPI. */
import assert from 'node:assert/strict';
import {chromium} from 'playwright';

const origin=process.env.PRACTICAMIA_ACCEPTANCE_ORIGIN||'http://127.0.0.1:8765';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)||process.env.PRACTICAMIA_E2E_LOCAL_ONLY!=='1')
  throw new Error('Acceptance must use an explicitly opted-in loopback server');
const health=await fetch(origin+'/__acceptance/health').then(r=>r.json());
assert.equal(health.synthetic,true);
const browser=await chromium.launch({headless:true});
const contexts=[];
const errors=[];
async function pageFor(subject){
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  contexts.push(context);
  await context.addCookies([{name:'acceptance_subject',value:subject,url:origin,sameSite:'Strict'}]);
  const page=await context.newPage();
  page.on('pageerror',error=>errors.push(String(error).slice(0,300)));
  return page;
}
try{
  const alice=await pageFor('alice');
  await alice.goto(origin+'/__acceptance/chat');
  await alice.getByRole('heading',{name:'How can I help?'}).waitFor({timeout:12000});
  const composer=alice.getByRole('textbox',{name:'Message PracticaMIA'});
  await composer.waitFor();
  assert.equal(await alice.getByRole('link',{name:'Sign out'}).count(),1);

  const message='I need help with my residence registration in Milan.';
  await composer.fill(message);
  await alice.getByRole('button',{name:'Send',exact:true}).click();
  await alice.getByText(message,{exact:true}).waitFor({timeout:20000});

  let recent=null;
  for(let i=0;i<60;i++){
    const response=await alice.request.get(origin+'/api/agent/conversations/recent');
    assert.equal(response.status(),200);
    recent=await response.json();
    if(recent.items?.length)break;
    await alice.waitForTimeout(150);
  }
  assert.ok(recent?.items?.length,'accepted message must create a persisted conversation');
  const threadId=recent.items[0].thread_id;
  assert.match(threadId,/^[0-9a-f-]{36}$/i);
  const ownHistory=await alice.request.get(origin+'/api/agent/threads/'+threadId+'/history');
  assert.equal(ownHistory.status(),200,'owner must resume their own conversation');

  const bob=await pageFor('bob');
  await bob.goto(origin+'/__acceptance/chat');
  await bob.getByRole('heading',{name:'How can I help?'}).waitFor({timeout:12000});
  const otherHistory=await bob.request.get(origin+'/api/agent/threads/'+threadId+'/history');
  assert.equal(otherHistory.status(),404,'another owner must not read this conversation');

  assert.deepEqual(errors,[],'chat workspace must not throw browser errors');
  process.stdout.write('PASS: single-chat root, persisted conversation, resume and owner isolation\n');
}finally{
  await Promise.all(contexts.map(context=>context.close()));
  await browser.close();
}

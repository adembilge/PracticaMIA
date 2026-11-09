/** Synthetic localhost Chromium acceptance scenarios over actual saved-case
 * React components and real FastAPI routes with temporary signed test users.
 * No Auth0 login, Vercel request, real personal data or government submission.
 */
import assert from 'node:assert/strict';
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {chromium} from 'playwright';

const origin=process.env.PRACTICAMIA_ACCEPTANCE_ORIGIN||'http://127.0.0.1:8765';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)||
   process.env.PRACTICAMIA_E2E_LOCAL_ONLY!=='1'){
  throw new Error('Browser acceptance must use an explicitly opted-in loopback server');
}
const output=resolve('.acceptance-results');
mkdirSync(output,{recursive:true});

const report={
  suite:'PracticaMIA synthetic browser-to-FastAPI acceptance',
  mode:'local-only; temporary RS256 identities; disposable PostgreSQL; synthetic approved-source fixture',
  externalAuth0Tested:false,
  realDocumentsTested:false,
  liveDeploymentTested:false,
  scenarios:[],
};
const errors=[];
const browser=await chromium.launch({headless:true});
const contexts=[];
let alicePage=null;
let caseId=null;
async function contextFor(subject){
  const context=await browser.newContext({acceptDownloads:true,viewport:{width:1440,height:950}});
  await context.addCookies([{name:'acceptance_subject',value:subject,url:origin,sameSite:'Strict'}]);
  contexts.push(context);
  const page=await context.newPage();
  page.on('pageerror',error=>errors.push({subject,error:String(error).slice(0,350)}));
  return page;
}
async function scenario(name,fn){
  const started=Date.now();
  try{
    await fn();
    report.scenarios.push({name,status:'passed',duration_ms:Date.now()-started});
    process.stdout.write('PASS '+name+'\n');
  }catch(error){
    const message=String(error?.stack||error).slice(0,1800);
    report.scenarios.push({name,status:'failed',duration_ms:Date.now()-started,error:message});
    process.stderr.write('FAIL '+name+': '+message+'\n');
    if(alicePage){
      await alicePage.screenshot({
        path:join(output,'failure-'+report.scenarios.length+'.png'),fullPage:true,
      }).catch(()=>{});
    }
  }
}
async function readJson(page,path){
  const response=await page.request.get(origin+path);
  return {status:response.status(),body:await response.json()};
}
async function scopeAnswers(page,values){
  for(let i=0;i<values.length;i++){
    const choice=values[i]==='yes'?'Yes':values[i]==='no'?'No':'Not sure';
    await page.getByRole('button',{name:choice,exact:true}).click();
    await page.getByRole('button',{name:'Save and continue'}).click();
    if(i<values.length-1){
      await page.getByText('QUESTION '+(i+2)+' / 5').waitFor({timeout:12000});
    }
  }
}
async function createCase(page){
  await page.goto(origin+'/cases/saved');
  await page.getByRole('button',{name:'Create an empty demo case'}).click();
  await page.waitForURL(/\/cases\/[0-9a-f]{8}-/i,{timeout:15000});
  const id=page.url().split('/').at(-1);
  assert.match(id,/^[0-9a-f]{8}-[0-9a-f-]{27,}$/);
  await page.getByText('QUESTION 1 / 5').waitFor({timeout:12000});
  return id;
}
async function confirmIntake(page,facts){
  for(const [field,value] of Object.entries(facts)){
    if(field==='move_in_date'){
      await page.locator('#intake-move-date').fill(value);
    }else{
      await page.locator('#intake-'+field).selectOption(value);
    }
  }
  await page.getByRole('checkbox',{
    name:/I checked these entries and confirm they describe this fictional example/,
  }).check();
  await page.getByRole('button',{name:'Confirm facts'}).click();
}
const facts={
  citizenship_class:'italian',
  registration_context:'already_registered_in_italy',
  destination_municipality:'milano',
  household_scope:'individual_no_aggregation',
  housing_basis:'registered_private_rental',
  move_in_date:'2026-11-05',
};

try{
  await scenario('A1: supported user creates, scopes, confirms and resumes a case',async()=>{
    alicePage=await contextFor('alice');
    caseId=await createCase(alicePage);
    await scopeAnswers(alicePage,['yes','yes','yes','no','yes']);
    await alicePage.getByRole('heading',{name:'Your demo scope check is complete.'})
      .waitFor({timeout:12000});
    await confirmIntake(alicePage,facts);
    await alicePage.locator('#case-workflow-checklist input[type="checkbox"]')
      .first().waitFor({timeout:15000});
    const {status,body}=await readJson(alicePage,'/api/cases/'+caseId+'/workflow');
    assert.equal(status,200);
    assert.equal(body.next_action,'review_checklist');
    assert.equal(body.checklist.items.length,5);
    assert.equal(body.package.download_allowed,true);
    assert.equal(body.official_submission,false);
    assert.equal(body.eligibility_evaluated,false);
    assert.equal(body.documents.enabled,false);
    assert.equal(await alicePage.locator('#case-workflow-checklist input[type="checkbox"]').count(),5);
  });

  await scenario('A2: all five user-read marks persist and draft PDF downloads',async()=>{
    assert.ok(alicePage&&caseId);
    for(let i=0;i<5;i++){
      await alicePage.locator('#case-workflow-checklist input[type="checkbox"]')
        .nth(i).check({timeout:12000});
      await alicePage.getByText('Actions read by you: '+(i+1)+' / 5')
        .waitFor({timeout:15000});
    }
    const link=alicePage.getByRole('link',{name:'Download PDF draft'});
    await link.waitFor({timeout:12000});
    const [download]=await Promise.all([
      alicePage.waitForEvent('download',{timeout:15000}),
      link.click(),
    ]);
    assert.equal(download.suggestedFilename(),'practicamia-preparation-draft.pdf');
    const savedPath=await download.path();
    assert.equal(readFileSync(savedPath).subarray(0,5).toString('ascii'),'%PDF-');
    await alicePage.reload();
    await alicePage.getByText('Actions read by you: 5 / 5')
      .waitFor({timeout:16000});
    assert.equal(await alicePage.locator('#case-workflow-checklist input[type="checkbox"]:checked').count(),5);
    const intake=await readJson(alicePage,'/api/cases/'+caseId+'/intake');
    assert.equal(intake.body.facts.move_in_date,'2026-11-05');
    assert.equal(intake.body.confirmed,true);
  });

  await scenario('A3: independent second account cannot inspect or export first case',async()=>{
    assert.ok(caseId);
    const bobPage=await contextFor('bob');
    const backend=await readJson(bobPage,'/api/cases/'+caseId);
    assert.equal(backend.status,404);
    assert.equal((await readJson(bobPage,'/api/cases/'+caseId+'/workflow')).status,404);
    assert.equal((await bobPage.request.get(origin+'/api/cases/'+caseId+'/package/pdf')).status(),404);
    await bobPage.goto(origin+'/cases/'+caseId);
    await bobPage.getByRole('heading',{name:'Case unavailable'}).waitFor({timeout:12000});
    const anonymous=await browser.newContext();
    try{
      assert.equal((await anonymous.request.get(origin+'/api/cases/'+caseId)).status(),401);
    }finally{await anonymous.close();}
  });

  await scenario('A4: revoked source blocks actions/PDF; restored evidence invalidates old marks',async()=>{
    assert.ok(alicePage&&caseId);
    const revoke=await alicePage.request.post(origin+'/__acceptance/sources/revoke');
    assert.equal(revoke.status(),200);
    await alicePage.getByRole('button',{name:'Refresh workflow'}).click();
    await alicePage.getByText(
      'The signed checklist is unavailable until the source evidence is approved.'
    ).waitFor({timeout:16000});
    assert.equal(await alicePage.getByRole('link',{name:'Download PDF draft'}).count(),0);
    assert.equal((await alicePage.request.get(
      origin+'/api/cases/'+caseId+'/package/pdf')).status(),409);
    const restore=await alicePage.request.post(origin+'/__acceptance/sources/restore');
    assert.equal(restore.status(),200);
    await alicePage.getByRole('button',{name:'Refresh workflow'}).click();
    await alicePage.getByText('Actions read by you: 0 / 5')
      .waitFor({timeout:16000});
    const state=(await readJson(alicePage,'/api/cases/'+caseId+'/workflow')).body;
    assert.equal(state.checklist.reviewed_count,0);
    assert.equal(state.package.download_allowed,true);
  });

  await scenario('A5: edited intake blocks unsupported case and clears prior review',async()=>{
    assert.ok(alicePage&&caseId);
    await alicePage.locator('#intake-housing_basis').selectOption('owner');
    await alicePage.getByRole('checkbox',{
      name:/I checked these entries and confirm they describe this fictional example/,
    }).check();
    await alicePage.getByRole('button',{name:'Confirm facts'}).click();
    await alicePage.getByText(
      'This example falls outside the supported route. Consult the official service.'
    ).waitFor({timeout:16000});
    assert.equal((await alicePage.request.get(
      origin+'/api/cases/'+caseId+'/package/pdf')).status(),409);
    await alicePage.locator('#intake-housing_basis').selectOption('registered_private_rental');
    await alicePage.getByRole('checkbox',{
      name:/I checked these entries and confirm they describe this fictional example/,
    }).check();
    await alicePage.getByRole('button',{name:'Confirm facts'}).click();
    await alicePage.getByText('Actions read by you: 0 / 5')
      .waitFor({timeout:16000});
  });

  await scenario('A6: unsupported and uncertain scope never exports an application',async()=>{
    const bobPage=await contextFor('bob');
    const unsupported=await createCase(bobPage);
    await bobPage.getByRole('button',{name:'No',exact:true}).click();
    await bobPage.getByRole('button',{name:'Save and continue'}).click();
    const first=await readJson(bobPage,'/api/cases/'+unsupported);
    assert.equal(first.body.status,'unsupported');
    assert.equal((await bobPage.request.get(
      origin+'/api/cases/'+unsupported+'/package/pdf')).status(),409);
    assert.equal((await readJson(bobPage,'/api/cases/'+unsupported+'/workflow')).body
      .checklist.items.length,0);
    const unsure=await createCase(bobPage);
    await scopeAnswers(bobPage,['yes','unsure']);
    assert.equal((await readJson(bobPage,'/api/cases/'+unsure)).body.status,
      'needs_information');
    assert.equal((await bobPage.request.get(
      origin+'/api/cases/'+unsure+'/package/pdf')).status(),409);
  });

  await scenario('A7: Italian UI preserves the same verified case logic',async()=>{
    assert.ok(alicePage&&caseId);
    await alicePage.getByRole('button',{name:'Toggle language'}).click();
    await alicePage.getByRole('heading',{name:'Percorso della pratica'})
      .waitFor({timeout:15000});
    await alicePage.getByText('Azioni lette: 0 / 5').waitFor({timeout:15000});
    const json=await readJson(alicePage,'/api/cases/'+caseId+'/workflow');
    assert.equal(json.body.official_submission,false);
    assert.equal(json.body.checklist.items.length,5);
    assert.equal(json.body.package.download_allowed,true);
    assert.equal(await alicePage.locator('#case-workflow-checklist input[type="checkbox"]').count(),5);
  });

  await scenario('A8: browser runs without uncaught runtime errors',async()=>{
    assert.deepEqual(errors,[]);
  });
}finally{
  await Promise.all(contexts.map(c=>c.close().catch(()=>{})));
  await browser.close();
  report.passed=report.scenarios.filter(s=>s.status==='passed').length;
  report.failed=report.scenarios.filter(s=>s.status==='failed').length;
  report.accepted=report.failed===0;
  report.caveats=[
    'Synthetic temporary JWT identity at the backend; not live Auth0 sign-in.',
    'Local first-route evidence resolver fixture; real signed-source registry tested separately.',
    'Real personal document processing remains release-gated.',
    'No deployed hostname or external government portal was contacted.',
  ];
  writeFileSync(join(output,'acceptance-report.json'),
    JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,failed:report.failed,
    accepted:report.accepted,output:join(output,'acceptance-report.json')}));
  if(!report.accepted) process.exitCode=1;
}

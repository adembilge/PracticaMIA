/** Synthetic localhost Chromium acceptance scenarios over actual saved-case
 * React components and real FastAPI routes with temporary signed test users.
 * No Auth0 login, Vercel request, real personal data or government submission.
 */
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {chromium} from 'playwright';
import {runDocumentScenarios} from './documents.mjs';

const origin=process.env.PRACTICAMIA_ACCEPTANCE_ORIGIN||'http://127.0.0.1:8765';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)||
   process.env.PRACTICAMIA_E2E_LOCAL_ONLY!=='1'){
  throw new Error('Browser acceptance must use an explicitly opted-in loopback server');
}
const output=resolve('.acceptance-results');
mkdirSync(output,{recursive:true});

const health=await fetch(origin+'/__acceptance/health').then(response=>response.json());
const report={
  suite:'PracticaMIA synthetic browser-to-FastAPI acceptance',
  mode:'local-only; temporary RS256 identities; disposable PostgreSQL; synthetic approved-source fixture',
  externalAuth0Tested:false,
  realDocumentsTested:false,
  syntheticVaultTested:health.private_documents===true,
  liveDeploymentTested:false,
  scenarios:[],
};
const errors=[];
const browser=await chromium.launch({headless:true});
const contexts=[];
let alicePage=null;
let caseId=null;
async function contextFor(subject,viewport={width:1440,height:950}){
  const context=await browser.newContext({acceptDownloads:true,viewport});
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
async function awaitSavedCaseStatus(page,id,expected){
  let last=null;
  for(let attempt=0;attempt<60;attempt++){
    const response=await readJson(page,'/api/cases/'+id);
    if(response.status===200){
      last=response.body.status;
      if(last===expected)return response.body;
    }
    await page.waitForTimeout(100);
  }
  throw new Error('Timed out waiting for saved case status '+expected+
    ', last observed: '+String(last));
}

async function awaitAgentStatus(page,url,status='completed'){
  for(let attempt=0;attempt<100;attempt++){
    const response=await readJson(page,url);
    assert.equal(response.status,200);
    if(response.body.status===status)return;
    await page.waitForTimeout(100);
  }
  throw new Error('Timed out waiting for agent run status '+status);
}

async function scopeAnswers(page,values){
  for(let i=0;i<values.length;i++){
    const choice=values[i]==='yes'?'Yes':values[i]==='no'?'No':'Not sure';
    await page.getByRole('button',{name:choice,exact:true}).click();
    const continues = values[i] === (i === 3 ? 'no' : 'yes');
    await page.getByRole('button',{name:continues ? 'Save and continue' : 'Save answer',exact:true}).click();
    if(i<values.length-1){
      await page.getByText('QUESTION '+(i+2)+' / 5').waitFor({timeout:12000});
    }
  }
}
async function createCase(page){
  await page.goto(origin+'/cases/saved');
  await page.getByRole('button',{name:'Start case'}).click();
  await page.waitForURL(/\/cases\/[0-9a-f]{8}-/i,{timeout:15000});
  const id=new URL(page.url()).pathname.split('/').at(-1);
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
    name:/I have reviewed the information above/,
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
  await scenario('Public case walkthrough: all four routes, corrections and restart',async()=>{
    const context=await browser.newContext({acceptDownloads:true,viewport:{width:390,height:800}});
    contexts.push(context);
    const page=await context.newPage();
    page.on('pageerror',error=>errors.push({subject:'visitor',error:String(error).slice(0,350)}));
    await page.goto(origin+'/cases/new');
    await page.getByRole('heading',{name:'Start a case',level:1}).waitFor();
    await page.getByRole('link',{name:/Explore a fictional case/}).click();
    const button=(name)=>page.getByRole('button',{name,exact:true});
    const choose=async(name)=>{
      await page.getByRole('button',{name:new RegExp('^'+name)}).click();
      await page.getByRole('heading',{name:'Questions',level:2}).waitFor();
      assert.doesNotMatch(await page.locator('section').innerText(),/\bdemo\b|fictional|simulat/i);
      await button('Continue').click();
    };
    const change=async()=>page.locator('section').getByRole('button',{name:'Choose another scenario'}).click();
    const documentStep=async()=>{
      await button('Review document').click();
      await button('Open sample document').click();
      await button('Confirm address').click();
    };
    const finish=async()=>{
      await button('Mark as reviewed').click();
      await button('Review draft').click();
      await page.getByRole('checkbox',{name:'I have checked the information above.'}).check();
      await button('Finish review').click();
      const downloadEvent=page.waitForEvent('download');
      await button('Download summary (JSON)').click();
      const download=await downloadEvent;
      const exported=JSON.parse(readFileSync(await download.path(),'utf8'));
      assert.equal(exported.simulation_only,true);
      assert.equal(exported.government_submission_status,'NOT_SUBMITTED');
      await page.getByRole('navigation',{name:'Case progress'}).getByRole('button',{name:/Review/}).click();
      await button('View summary').click();
      await page.getByRole('heading',{name:'Review complete'}).waitFor();
      await change();
    };
    await choose('Standard move');
    await documentStep();
    await finish();
    await choose('Missing information');
    await page.getByRole('status').getByText('More information needed').waitFor();
    await button('Review answers').click();
    const registration=page.getByRole('group',{name:'Were you already registered in Italy?'});
    await registration.getByRole('button',{name:'Yes',exact:true}).click();
    await button('Continue').click();
    await page.getByRole('status').getByText('Review a housing document').waitFor();
    await page.getByRole('navigation',{name:'Case progress'}).getByRole('button',{name:/Scenario/}).click();
    await choose('Different circumstances');
    await page.getByRole('status').getByText('This situation needs a different route').waitFor();
    await change();
    await choose('Document mismatch');
    await documentStep();
    await page.getByRole('status').getByText(/The addresses differ/).waitFor();
    assert.equal(await button('Review draft').isEnabled(),false);
    await page.getByLabel('Address to use').selectOption({index:0});
    await button('Confirm address').click();
    await finish();
  });

  await scenario('A1: a move within Milan reaches the signed checklist',async()=>{
    alicePage=await contextFor('alice');
    caseId=await createCase(alicePage);
    const accountLink=alicePage.getByRole('link',{name:'Example Applicant',exact:true});
    await accountLink.waitFor({timeout:12000});
    assert.equal(await accountLink.getAttribute('href'),'/account');
    const journey=alicePage.getByRole('navigation',{name:'Case progress'});
    const intakeStep=journey.getByRole('button',{name:/^02 Case details/});
    assert.match(await intakeStep.innerText(),/Finish the initial questions first/);
    await intakeStep.click();
    await alicePage.getByRole('heading',{name:'Scope',exact:true}).waitFor();
    await alicePage.getByRole('heading',{
      name:'Before you moved, were you registered as a resident in Italy?',
    }).waitFor();
    await scopeAnswers(alicePage,['yes','yes','yes','no','yes']);
    await alicePage.getByRole('heading',{name:'Case details',exact:true})
      .waitFor({timeout:12000});
    await alicePage.getByRole('button',{name:/^01 Scope/}).click();
    await alicePage.getByRole('heading',{name:'Initial questions complete.'}).waitFor();
    await alicePage.goBack();
    await alicePage.getByRole('heading',{name:'Case details',exact:true}).waitFor();
    assert.doesNotMatch(await intakeStep.innerText(),/Finish the initial questions first/);
    await confirmIntake(alicePage,facts);
    await alicePage.getByRole('button',{name:'Requirements →',exact:true}).click();
    await alicePage.locator('#case-workflow-checklist input[type="checkbox"]')
      .first().waitFor({timeout:15000});
    const {status,body}=await readJson(alicePage,'/api/cases/'+caseId+'/workflow');
    assert.equal(status,200);
    assert.equal(body.next_action,'review_checklist');
    assert.equal(body.checklist.items.length,5);
    assert.equal(body.package.download_allowed,true);
    assert.equal(body.official_submission,false);
    assert.equal(body.eligibility_evaluated,false);
    assert.equal(body.documents.enabled,health.private_documents);
    assert.equal(await alicePage.locator('#case-workflow-checklist input[type="checkbox"]').count(),5);
    const requirement=alicePage.locator('.requirement-open').first();
    await requirement.click();
    await alicePage.getByRole('dialog').waitFor();
    await alicePage.keyboard.press('Escape');
    await requirement.evaluate(button=>new Promise(resolve=>requestAnimationFrame(()=>resolve(document.activeElement===button)))).then(focused=>assert.equal(focused,true));
  });

  await scenario('A9: an applicant moving from another Italian municipality can resume and reach the signed checklist',async()=>{
    const page=await contextFor('alice');
    const id=await createCase(page);
    // A saved No from the former Milan-only question stays blocked until corrected.
    await scopeAnswers(page,['no']);
    await awaitSavedCaseStatus(page,id,'unsupported');
    await page.reload();
    await page.getByText(
      'If your previous registered address was in Milan or another Italian municipality, select Yes.'
    ).waitFor({timeout:12000});
    assert.equal(await page.getByRole('button',{name:'No',exact:true}).getAttribute('aria-pressed'),'true');
    await scopeAnswers(page,['yes','yes','yes','no','yes']);
    await confirmIntake(page,facts);
    await page.locator('#case-workflow-checklist input[type="checkbox"]')
      .first().waitFor({timeout:15000});
    const {status,body}=await readJson(page,'/api/cases/'+id+'/workflow');
    assert.equal(status,200);
    assert.equal(body.checklist.items.length,5);
    assert.equal(body.package.download_allowed,true);
    assert.equal(body.official_submission,false);
  });

  await scenario('A2: all five user-read marks persist and draft PDF downloads',async()=>{
    assert.ok(alicePage&&caseId);
    for(let i=0;i<5;i++){
      // This checkbox is controlled by the server-acknowledged review state.
      // A click triggers PATCH; unlike .check(), it does not require an
      // immediate local checked state before the async response resolves.
      await alicePage.locator('#case-workflow-checklist input[type="checkbox"]')
        .nth(i).click({timeout:12000});
      await alicePage.getByText('Actions read by you: '+(i+1)+' / 5')
        .waitFor({timeout:15000});
    }
    await alicePage.getByRole('button',{name:/^05 PDF summary/}).click();
    const link=alicePage.getByRole('link',{name:'Download PDF draft'});
    await link.waitFor({timeout:12000});
    const [download]=await Promise.all([
      alicePage.waitForEvent('download',{timeout:15000}),
      link.click(),
    ]);
    assert.equal(download.suggestedFilename(),'practicamia-preparation-draft.pdf');
    const savedPath=await download.path();
    assert.equal(readFileSync(savedPath).subarray(0,5).toString('ascii'),'%PDF-');
    const text = execFileSync('pdftotext',[savedPath,'-'],{encoding:'utf8'});
    assert.match(text, /What to prepare for ANPR/);
    assert.match(text, /Ufficio di/);
    await alicePage.getByRole('heading',{name:'What to prepare for ANPR'}).waitFor();
    await alicePage.reload();
    await alicePage.getByRole('heading',{name:'PDF summary',exact:true}).waitFor();
    await alicePage.getByRole('button',{name:/^03 Requirements/}).click();
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
    const unavailable=bobPage.getByRole('heading',{level:1,name:'Case unavailable'});
    await unavailable.waitFor({timeout:12000});
    assert.equal(await bobPage.getByRole('heading',{name:'Milan residence change'}).count(),0);
    assert.equal(await bobPage.getByRole('button',{name:'Try again'}).count(),0);
    const back=bobPage.getByRole('link',{name:'Back to saved cases'});
    assert.equal(await back.getAttribute('href'),'/cases/saved');
    await bobPage.setViewportSize({width:390,height:844});
    assert.equal(await bobPage.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
    await back.click();
    await bobPage.waitForURL(origin+'/cases/saved');

    const caseApi=origin+'/api/cases/'+caseId;
    const failLoad=route=>route.fulfill({status:503,body:'{}'});
    await alicePage.route(caseApi,failLoad);
    await alicePage.goto(origin+'/cases/'+caseId);
    await alicePage.getByRole('heading',{level:1,name:'We couldn’t load this case'}).waitFor({timeout:12000});
    await alicePage.unroute(caseApi,failLoad);
    await alicePage.getByRole('button',{name:'Try again',exact:true}).click();
    await alicePage.getByRole('navigation',{name:'Case progress'}).waitFor({timeout:12000});
    const anonymous=await browser.newContext();
    try{
      assert.equal((await anonymous.request.get(origin+'/api/cases/'+caseId)).status(),401);
      const guestPage=await anonymous.newPage();
      await guestPage.setViewportSize({width:375,height:812});
      await guestPage.goto(origin+'/cases/saved');
      const signIn=guestPage.getByRole('link',{name:'Sign in / Register',exact:true});
      await signIn.waitFor({timeout:12000});
      assert.equal(await signIn.getAttribute('href'),'/account');
      await guestPage.getByRole('button',{name:'Switch to Italian'}).click();
      await guestPage.getByRole('link',{name:'Accedi / Registrati',exact:true}).waitFor({timeout:12000});
    }finally{await anonymous.close();}
  });

  await scenario('A4: revoked source blocks actions/PDF; restored evidence invalidates old marks',async()=>{
    assert.ok(alicePage&&caseId);
    const before=(await readJson(alicePage,'/api/cases/'+caseId+'/workflow')).body;
    assert.equal(before.checklist.reviewed_count,5,
      'Revocation scenario requires previously saved review marks');
    const revoke=await alicePage.request.post(origin+'/__acceptance/sources/revoke');
    assert.equal(revoke.status(),200);
    await alicePage.getByRole('button',{name:'Refresh workflow'}).click();
    await alicePage.getByRole('status').filter({
      hasText:'The signed checklist is unavailable until the source evidence is approved.',
    }).waitFor({timeout:16000});
    await alicePage.getByRole('button',{name:/^05 PDF summary/}).click();
    await alicePage.getByText('Preparation draft blocked').waitFor();
    assert.equal(await alicePage.getByRole('link',{name:'Download PDF draft'}).count(),0);
    assert.equal((await alicePage.request.get(
      origin+'/api/cases/'+caseId+'/package/pdf')).status(),409);
    const restore=await alicePage.request.post(origin+'/__acceptance/sources/restore');
    assert.equal(restore.status(),200);
    await alicePage.getByRole('button',{name:'Refresh workflow'}).click();
    await alicePage.getByRole('button',{name:/^03 Requirements/}).click();
    await alicePage.getByText('Actions read by you: 0 / 5')
      .waitFor({timeout:16000});
    const state=(await readJson(alicePage,'/api/cases/'+caseId+'/workflow')).body;
    assert.equal(state.checklist.reviewed_count,0);
    assert.equal(state.package.download_allowed,true);
  });

  await scenario('A5: edited intake blocks unsupported case and clears prior review',async()=>{
    assert.ok(alicePage&&caseId);
    await alicePage.getByRole('button',{name:/^02 Case details/}).click();
    await alicePage.locator('#intake-housing_basis').selectOption('owner');
    await alicePage.getByRole('checkbox',{
      name:/I have reviewed the information above/,
    }).check();
    await alicePage.getByRole('button',{name:'Confirm facts'}).click();
    await alicePage.getByText(
      'This example falls outside the supported route. Consult the official service.'
    ).waitFor({timeout:16000});
    assert.equal((await alicePage.request.get(
      origin+'/api/cases/'+caseId+'/package/pdf')).status(),409);
    await alicePage.locator('#intake-housing_basis').selectOption('registered_private_rental');
    await alicePage.getByRole('checkbox',{
      name:/I have reviewed the information above/,
    }).check();
    await alicePage.getByRole('button',{name:'Confirm facts'}).click();
    await alicePage.getByRole('button',{name:/^03 Requirements/}).click();
    await alicePage.getByText('Actions read by you: 0 / 5')
      .waitFor({timeout:16000});
  });

  await scenario('A6: unsupported and uncertain scope never exports an application',async()=>{
    const bobPage=await contextFor('bob');
    const unsupported=await createCase(bobPage);
    await bobPage.getByRole('button',{name:'No',exact:true}).click();
    await bobPage.getByRole('button',{name:'Save answer',exact:true}).click();
    const first=await awaitSavedCaseStatus(bobPage,unsupported,'unsupported');
    assert.equal(first.status,'unsupported');
    assert.equal((await bobPage.request.get(
      origin+'/api/cases/'+unsupported+'/package/pdf')).status(),409);
    assert.equal((await readJson(bobPage,'/api/cases/'+unsupported+'/workflow')).body
      .checklist.items.length,0);
    const otherDestination=await createCase(bobPage);
    await scopeAnswers(bobPage,['yes','no']);
    await awaitSavedCaseStatus(bobPage,otherDestination,'unsupported');
    assert.equal((await bobPage.request.get(
      origin+'/api/cases/'+otherDestination+'/package/pdf')).status(),409);
    const unsure=await createCase(bobPage);
    await scopeAnswers(bobPage,['yes','unsure']);
    const uncertain=await awaitSavedCaseStatus(bobPage,unsure,'needs_information');
    assert.equal(uncertain.status,'needs_information');
    assert.equal((await bobPage.request.get(
      origin+'/api/cases/'+unsure+'/package/pdf')).status(),409);
  });

  await scenario('A7: Italian UI preserves the same verified case logic',async()=>{
    assert.ok(alicePage&&caseId);
    await alicePage.getByRole('button',{name:'Switch to Italian'}).click();
    await alicePage.getByRole('heading',{name:'Requisiti',exact:true})
      .waitFor({timeout:15000});
    await alicePage.getByRole('button',{name:/^01 Ambito/}).click();
    await alicePage.getByRole('button',{
      name:/Prima del trasferimento, avevi la residenza anagrafica in Italia/,
    }).waitFor({timeout:12000});
    await alicePage.getByRole('button',{name:/^03 Requisiti/}).click();
    await alicePage.getByText('Azioni lette: 0 / 5').waitFor({timeout:15000});
    const json=await readJson(alicePage,'/api/cases/'+caseId+'/workflow');
    assert.equal(json.body.official_submission,false);
    assert.equal(json.body.checklist.items.length,5);
    assert.equal(json.body.package.download_allowed,true);
    assert.equal(await alicePage.locator('#case-workflow-checklist input[type="checkbox"]').count(),5);
  });

  await scenario('Mobile: case progress opens a keyboard-accessible requirement sheet',async()=>{
    const page=await contextFor('alice',{width:390,height:844});
    await page.goto(origin+'/cases/'+caseId);
    await page.getByRole('button',{name:/^03 Requirements/}).click();
    const trigger=page.locator('.requirement-open').first();
    await trigger.click();
    const dialog=page.getByRole('dialog');
    await dialog.waitFor();
    assert.equal(await dialog.evaluate(panel=>panel.matches(':modal')),true);
    await page.keyboard.press('Escape');
    await dialog.waitFor({state:'hidden'});
    await trigger.evaluate(button=>new Promise(resolve=>requestAnimationFrame(()=>resolve(document.activeElement===button)))).then(focused=>assert.equal(focused,true));
  });

  await scenario('Mobile Italian: a downloaded PDF opens with the cited ANPR worksheet',async()=>{
    const page=await contextFor('alice',{width:390,height:844});
    await page.goto(origin+'/cases/'+caseId);
    await page.getByRole('button',{name:'Switch to Italian'}).click();
    await page.getByRole('button',{name:/^05 Riepilogo PDF/}).click();
    await page.getByRole('heading',{name:'Dati da preparare per ANPR'}).waitFor();
    const [download]=await Promise.all([
      page.waitForEvent('download',{timeout:15000}),
      page.locator('#case-workflow-package a[href$="lang=it"]').click(),
    ]);
    const file=await download.path();
    const text=execFileSync('pdftotext',[file,'-'],{encoding:'utf8'});
    assert.match(text,/Dati da preparare per ANPR/);
    assert.match(text,/BOZZA - NON INVIATA/);
    assert.match(text,/Al numero/);
  });

  await scenario('Saved case archive: restore a completed case with its checklist and PDF',async()=>{
    const owner=await contextFor('alice');
    const second=await contextFor('bob');
    const casePath='/cases/'+caseId;
    const api='/api'+casePath;
    const original=(await readJson(owner,api+'/workflow')).body;
    await owner.goto(origin+casePath);
    await owner.getByText('Manage this case',{exact:true}).click();
    await owner.getByRole('button',{name:'Archive case',exact:true}).click();
    await owner.getByText('Case archived.',{exact:true}).waitFor();
    assert.equal((await second.request.patch(origin+api+'/archive',{data:{archived:false}})).status(),404);
    assert.equal((await readJson(owner,'/api/cases')).body.some(row=>row.id===caseId),false);
    assert.equal((await readJson(owner,'/api/cases?view=archived')).body.some(row=>row.id===caseId),true);
    await owner.goto(origin+'/cases/saved');
    await owner.getByRole('button',{name:'Archived',exact:true}).click();
    await owner.locator('.saved-case-list a[href="'+casePath+'"]').click();
    await owner.getByText('Case archived.',{exact:true}).waitFor();
    await owner.getByText('Manage this case',{exact:true}).click();
    await owner.getByRole('button',{name:'Restore to active cases',exact:true}).click();
    await owner.getByRole('button',{name:'Archive case',exact:true}).waitFor();
    const restored=(await readJson(owner,api+'/workflow')).body;
    assert.deepEqual(restored.checklist.reviewed_items,original.checklist.reviewed_items);
    assert.equal((await owner.request.get(origin+api+'/package/pdf')).status(),200);
  });

  if(health.private_documents) await runDocumentScenarios({
    origin, scenario, contextFor, createCase, scopeAnswers, confirmIntake, facts, readJson,
  });

  await scenario('Preparation Preview: mobile deep link, OCR feedback, and load recovery',async()=>{
    const page=await contextFor('alice',{width:360,height:820});
    const id='11111111-1111-4111-8111-111111111111';
    const path='/cases/'+id+'/preparation';
    let unavailable=false;
    const historicalPassage = '00000000-0000-4000-8000-000000000031:0001';
    let finishExtraction, finishUpload;
    const extractionResponse=new Promise(resolve=>{finishExtraction=resolve;});
    const uploadResponse=new Promise(resolve=>{finishUpload=resolve;});
    await page.route('**/api'+path+'**',async route=>{
      const endpoint=new URL(route.request().url()).pathname;
      if(endpoint.endsWith('/extract')){
        await extractionResponse;
        return route.fulfill({status:503,json:{}});
      }
      if(endpoint.endsWith('/documents')&&route.request().method()==='POST'){
        await uploadResponse;
        return route.fulfill({status:201,json:{}});
      }
      if(endpoint.endsWith('/conversation')) return route.fulfill({json:{
        is_demo:true,historical_only:true,government_submission_status:'not_submitted',
        turns:[{
          id:'history-test',question:'What did the source say?',answer:'Stored message.',
          action:'evidence',status:'answer_generated',language:'en',next_action:null,
          created_at:'2026-11-17T20:00:00Z',citation_status:'historical',citations:[{
            source_id:'fictional-source',source_version_id:historicalPassage.split(':')[0],
            passage_id:historicalPassage,source_revision:1,status:'historical',
          }],
        }],
      }});
      if(endpoint.endsWith('/documents')) return route.fulfill({json:[{
        id,document_type:'fictional_agreement',extraction_status:'not_processed',
        status:'uploaded',candidates:[],confirmed_fields:{},
      }]});
      if(endpoint !== '/api'+path) return route.fulfill({status:404,json:{}});
      if(unavailable) return route.fulfill({status:503,json:{}});
      return route.fulfill({json:{
        is_demo:true,confirmed_facts:{},user_reviewed:false,
        intake:{is_legal_assessment:false,status:'needs_information',answered_count:0,total_questions:5,
          next_question:{field:'citizenship_class',label_en:'Citizenship for this example',
            label_it:'Cittadinanza per questo esempio',
            options:[{value:'italian',label_en:'Italian',label_it:'Italiana'}]}},
        workflow:{status:'needs_information',blocking_issues:[],package:null,
          rules:{decision:'needs_information',checklist:[],missing_fields:[]}},
      }});
    });
    await page.goto(origin+path+'#synthetic-documents');
    await page.getByRole('heading',{name:'Synthetic documents',exact:true}).waitFor();
    assert.equal(await page.getByRole('heading',{name:'Guided intake',exact:true}).isVisible(),false);
    await page.locator('input[type=file]').setInputFiles({
      name:'synthetic.pdf',mimeType:'application/pdf',buffer:Buffer.from('synthetic test'),
    });
    await page.getByRole('checkbox',{name:'I confirm that this file contains no real personal information'}).check();
    const uploading=page.getByRole('status').filter({hasText:'Uploading file…'});
    try{
      await page.getByRole('button',{name:'Upload',exact:true}).click();
      await uploading.waitFor();
      const track=uploading.locator('.document-progress-track');
      assert.equal(await track.isVisible(),true);
      await page.emulateMedia({reducedMotion:'reduce'});
      assert.equal(await track.isVisible(),false);
      assert.equal(await uploading.isVisible(),true);
      await page.emulateMedia({reducedMotion:null});
    }finally{finishUpload();}
    await page.getByRole('status').filter({hasText:'Synthetic file uploaded.'}).waitFor();
    await uploading.waitFor({state:'hidden'});
    const extracting=page.getByRole('status').filter({hasText:'Extracting text…'});
    try{
      await page.getByRole('button',{name:'Extract text',exact:true}).click();
      await extracting.waitFor();
    }finally{finishExtraction();}
    await page.getByRole('alert').filter({hasText:'Text extraction is unavailable. Your file is saved.'}).waitFor();
    await extracting.waitFor({state:'hidden'});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.getByRole('button',{name:'Case details',exact:true}).click();
    await page.getByLabel('Citizenship for this example').selectOption('italian');
    await page.getByRole('button',{name:'Case guide',exact:true}).click();
    await page.getByRole('heading',{name:'Case guide',exact:true}).waitFor();
    await page.getByText('A citation is no longer available for current use.',{exact:false}).waitFor();
    await page.getByText(historicalPassage,{exact:true}).waitFor();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.goBack();
    assert.equal(await page.getByLabel('Citizenship for this example').inputValue(),'italian');
    await page.getByRole('button',{name:'Synthetic documents',exact:true}).click();
    await page.getByRole('button',{name:'Switch to Italian'}).click();
    await page.getByRole('heading',{name:'Documenti sintetici',exact:true}).waitFor();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    unavailable=true;
    await page.reload();
    await page.getByRole('heading',{name:'Could not load the preview'}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Upload',exact:true}).isVisible(),false);
    unavailable=false;
    await page.getByRole('button',{name:'Try again',exact:true}).click();
    await page.getByRole('heading',{name:'Synthetic documents',exact:true}).waitFor();
  });

  await scenario('Agent reconnect: a new browser session replies and the queued worker completes the run',async()=>{
    const route='/__acceptance/agent';
    const original=await contextFor('alice');
    await original.goto(origin+route);
    await original.getByRole('button',{name:'Open conversation'}).first().click();
    await original.getByText('Which synthetic municipality applies?',{exact:true}).waitFor();
    await original.context().close();

    const owner=await contextFor('alice',{width:390,height:800});
    await owner.goto(origin+route);
    await owner.getByRole('button',{name:'Open conversation'}).first().click();
    await owner.getByText('Which synthetic municipality applies?',{exact:true}).waitFor();
    await owner.getByRole('radio',{name:'Fixture B'}).check();
    const sent=[];
    await owner.route('**/questions/*/reply',async intercepted=>{
      const response=await intercepted.fetch();
      sent.push({status:response.status(),body:await response.json()});
      // Simulate a response lost after the server committed the reply.
      if(sent.length===1) await intercepted.abort();
      else await intercepted.fulfill({response});
    });
    const reply=owner.getByRole('button',{name:'Send reply',exact:true});
    await reply.click();
    await owner.getByRole('alert').filter({hasText:'Could not confirm the reply. Try again.'}).waitFor();
    await reply.click();
    await reply.waitFor({state:'hidden'});
    assert.equal(sent.length,2);
    assert.equal(sent[0].status,200);
    assert.deepEqual(sent[1],sent[0]);

    const other=await contextFor('bob');
    await other.goto(origin+route);
    await other.getByText('No active conversations.',{exact:true}).waitFor();
    const run=sent[0].body;
    const url=`/api/agent/threads/${run.thread_id}/runs/${run.run_id}`;
    assert.equal((await readJson(other,url)).status,404);
    assert.equal((await readJson(other,url+'/events')).status,404);

    await awaitAgentStatus(owner,url);
    const completed=owner.getByRole('heading',{name:'Conversation complete'});
    if(!await completed.isVisible()) await owner.getByRole('button',{name:'Check status'}).click();
    await completed.waitFor();
    await owner.getByText('Received Fixture B.',{exact:true}).waitFor();
    const replay=await readJson(owner,url+'/events');
    assert.equal(replay.status,200);
    assert.deepEqual(replay.body.events.map(event=>event.type),[
      'run.started','question.requested','question.answered','answer.completed',
    ]);
    const [citation]=replay.body.events.at(-1).result.citations;
    const sourceUrl=url+'/sources/'+encodeURIComponent(citation.citation_id);
    assert.equal((await readJson(other,sourceUrl)).status,404);
    const [sourceResponse]=await Promise.all([
      owner.waitForResponse(response=>new URL(response.url()).pathname===sourceUrl),
      owner.getByRole('button',{name:'View cited passage'}).click(),
    ]);
    assert.equal(sourceResponse.status(),200);
    const source=await sourceResponse.json();
    assert.equal(source.passage.citation.passage_id,citation.passage_id);
    const quote=owner.locator('blockquote[lang="it"]');
    await quote.getByText('Questo esempio sintetico riguarda il cambio di residenza.',{exact:true}).waitFor();
    const terms=owner.locator('section[lang="en"]');
    await terms.getByText('cambio di residenza',{exact:true}).waitFor();
    await terms.getByText('Updating the address recorded for your registered residence.',{exact:true}).waitFor();
    assert.equal(await owner.getByRole('link',{name:'Open the official page'}).getAttribute('href'),citation.official_url);
    assert.equal(await owner.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  });

  await scenario('Agent clarification: a free-text date can be corrected after validation',async()=>{
    const owner=await contextFor('alice',{width:390,height:800});
    await owner.goto(origin+'/__acceptance/agent');
    await owner.getByRole('button',{name:'Open conversation'}).first().click();
    await owner.getByText('What was the synthetic move-in date?',{exact:true}).waitFor();
    const field=owner.getByLabel('Your reply');
    const send=owner.getByRole('button',{name:'Send reply',exact:true});
    const nextReply=()=>owner.waitForResponse(response=>
      response.request().method()==='POST' && /\/questions\/[^/]+\/reply$/.test(new URL(response.url()).pathname),
    );

    await field.fill('2026-02-30');
    const [invalid]=await Promise.all([nextReply(),send.click()]);
    assert.equal(invalid.status(),422);
    await owner.getByRole('alert').filter({
      hasText:'Enter a valid move-in date in YYYY-MM-DD or DD/MM/YYYY format.',
    }).waitFor();
    assert.equal(await field.inputValue(),'2026-02-30');
    const pendingUrl=new URL(invalid.url()).pathname.split('/questions/')[0];
    const pending=await readJson(owner,pendingUrl+'/events');
    assert.deepEqual(pending.body.events.map(event=>event.type),['run.started','question.requested']);

    await field.fill('18/11/2026');
    const [valid]=await Promise.all([nextReply(),send.click()]);
    assert.equal(valid.status(),200);
    await send.waitFor({state:'hidden'});
    await awaitAgentStatus(owner,pendingUrl);
    const completed=owner.getByRole('heading',{name:'Conversation complete'});
    if(!await completed.isVisible()) await owner.getByRole('button',{name:'Check status'}).click();
    await completed.waitFor();
    await owner.getByText('Received 18/11/2026.',{exact:true}).waitFor();
    const replay=await readJson(owner,pendingUrl+'/events');
    assert.equal(replay.status,200);
    assert.deepEqual(replay.body.events.map(event=>event.type),[
      'run.started','question.requested','question.answered','answer.completed',
    ]);
    const [, , answered, terminal]=replay.body.events;
    assert.equal(answered.text,'18/11/2026');
    assert.equal(terminal.result.explanation,'Received 18/11/2026.');
  });

  await scenario('Agent clarification: changing topics releases the pending question',async()=>{
    const owner=await contextFor('alice',{width:390,height:800});
    owner.setDefaultTimeout(10000);
    await owner.goto(origin+'/__acceptance/agent');
    await owner.getByRole('button',{name:'Open conversation'}).first().click();
    await owner.getByText('Which synthetic detail should stay open when changing topics?',{exact:true}).waitFor();
    const change=owner.getByRole('button',{name:'Change topic',exact:true});
    const [accepted]=await Promise.all([
      owner.waitForResponse(response=>response.request().method()==='POST' && response.url().endsWith('/reply')),
      change.click(),
    ]);
    assert.equal(accepted.status(),200);
    await change.waitFor({state:'hidden'});
    const url=new URL(accepted.url()).pathname.split('/questions/')[0];
    await awaitAgentStatus(owner,url);
    const completed=owner.getByRole('heading',{name:'Topic changed'});
    if(!await completed.isVisible()) await owner.getByRole('button',{name:'Check status'}).click();
    await completed.waitFor();
    const replay=await readJson(owner,url+'/events');
    assert.equal(replay.status,200);
    assert.deepEqual(replay.body.events.map(event=>event.type),[
      'run.started','question.requested','question.answered','answer.completed',
    ]);
    const [, , reply, terminal]=replay.body.events;
    assert.equal(reply.disposition,'change_topic');
    assert.equal(reply.text,null);
    assert.deepEqual(terminal.result.missing_information,['jurisdiction']);
    assert.equal(terminal.result.verification_status,'insufficient_evidence');
  });

  await scenario('Agent clarification: stale tabs recover without answering the new question',async()=>{
    const viewport={width:390,height:800};
    const owner=await contextFor('alice',viewport);
    const stale=await contextFor('alice',viewport);
    const offline=await contextFor('alice',viewport);
    const first='Which synthetic detail should both tabs see first?';
    const next='Which synthetic detail should the refreshed tab see?';
    for(const page of [owner,stale,offline]){
      page.setDefaultTimeout(10000);
      await page.goto(origin+'/__acceptance/agent');
      await page.getByRole('button',{name:'Open conversation'}).first().click();
      await page.getByText(first,{exact:true}).waitFor();
      await page.getByRole('radio',{name:page===owner?'Fixture A':'Fixture B'}).check();
    }
    process.stdout.write('Agent stale tabs: each session opened the first question\n');

    const submit=async page=>{
      const [response]=await Promise.all([
        page.waitForResponse(result=>result.request().method()==='POST' && result.url().endsWith('/reply')),
        page.getByRole('button',{name:'Send reply',exact:true}).click(),
      ]);
      return response;
    };
    const accepted=await submit(owner);
    assert.equal(accepted.status(),200);
    const url=new URL(accepted.url()).pathname.split('/questions/')[0];
    process.stdout.write('Agent stale tabs: the first reply was accepted\n');
    await awaitAgentStatus(owner,url,'waiting_for_information');
    process.stdout.write('Agent stale tabs: the worker requested a replacement question\n');

    const rejected=await submit(stale);
    assert.equal(rejected.status(),409);
    await stale.getByRole('alert').filter({hasText:'This reply was rejected because the conversation changed.'}).waitFor();
    await stale.getByText(next,{exact:true}).waitFor();
    assert.equal(await stale.getByRole('radio',{name:'Fixture B'}).isChecked(),false);
    assert.equal(await stale.getByRole('button',{name:'Send reply',exact:true}).isEnabled(),false);
    process.stdout.write('Agent stale tabs: automatic refresh recovered the replacement\n');

    await offline.route(origin+url,route=>route.fulfill({status:503}),{times:1});
    assert.equal((await submit(offline)).status(),409);
    await offline.getByRole('alert').filter({hasText:'Check status to reload it.'}).waitFor();
    await offline.getByText(first,{exact:true}).waitFor({state:'hidden'});
    assert.equal(await offline.getByRole('button',{name:'Send reply',exact:true}).isVisible(),false);
    await offline.getByRole('button',{name:'Check status',exact:true}).click();
    await offline.getByText(next,{exact:true}).waitFor();
    process.stdout.write('Agent stale tabs: manual retry recovered after a failed refresh\n');

    const replay=await readJson(owner,url+'/events');
    assert.equal(replay.status,200);
    assert.deepEqual(replay.body.events.map(event=>event.type),[
      'run.started','question.requested','question.answered','question.requested',
    ]);
    const [,requested,firstReply,replacement]=replay.body.events;
    assert.equal(firstReply.question_id,requested.question.question_id);
    assert.equal(firstReply.text,'Fixture A');
    await offline.getByRole('radio',{name:'Fixture B'}).check();
    const fresh=await submit(offline);
    assert.equal(fresh.status(),200);
    await awaitAgentStatus(offline,url);
    const completed=await readJson(offline,url+'/events?after_seq='+replacement.event_seq);
    assert.equal(completed.status,200);
    assert.deepEqual(completed.body.events.map(event=>event.type),['question.answered','answer.completed']);
    const [freshReply]=completed.body.events;
    assert.equal(freshReply.question_id,replacement.question.question_id);
    assert.equal(freshReply.text,'Fixture B');
    assert.notEqual(freshReply.client_reply_id,firstReply.client_reply_id);
  });

  await scenario('Agent stop: refresh a stale revision and remove the stopped conversation from discovery',async()=>{
    const route='/__acceptance/agent';
    const owner=await contextFor('alice',{width:390,height:800});
    await owner.goto(origin+route);
    const [opened]=await Promise.all([
      owner.waitForResponse(response=>
        response.request().method()==='GET' && /\/api\/agent\/threads\/[^/]+\/runs\/[^/?]+$/.test(response.url()),
      ),
      owner.getByRole('button',{name:'Open conversation'}).last().click(),
    ]);
    const url=new URL(opened.url()).pathname;
    await owner.getByText('Which synthetic route should be stopped?',{exact:true}).waitFor();
    const requests=[];
    await owner.route('**/runs/*/stop',async intercepted=>{
      const body=intercepted.request().postDataJSON();
      // Model a stale revision while leaving the server's validation path intact.
      const response=await intercepted.fetch(requests.length===0
        ? {postData:{expected_run_revision:body.expected_run_revision-1}}
        : {});
      requests.push(response.status());
      await intercepted.fulfill({response});
    });

    const stop=owner.getByRole('button',{name:'Stop conversation',exact:true});
    await stop.click();
    await owner.getByRole('alert').filter({hasText:'The conversation changed. Review its current status.'}).waitFor();
    assert.deepEqual(requests,[409]);
    assert.equal(await owner.getByRole('button',{name:'Send reply'}).isVisible(),true);

    await stop.click();
    await owner.getByRole('heading',{name:'Conversation stopped',exact:true}).waitFor();
    assert.deepEqual(requests,[409,200]);
    assert.equal(await owner.getByRole('button',{name:'Send reply'}).isVisible(),false);
    assert.equal(await stop.isVisible(),false);

    const replay=await readJson(owner,url+'/events');
    assert.equal(replay.status,200);
    assert.deepEqual(replay.body.events.map(event=>event.type),['run.started','question.requested','run.stopped']);
    assert.deepEqual(replay.body.events.at(-1).committed_operation_ids,[]);
    const stoppedRun=replay.body.run_id;
    await owner.reload();
    await owner.getByRole('heading',{name:'Active conversations',exact:true}).waitFor();
    const active=await readJson(owner,'/api/agent/runs/active');
    assert.equal(active.status,200);
    assert.equal(active.body.items.some(run=>run.run_id===stoppedRun),false);
  });

  await scenario('Agent reconnect: exhausted catalogue retries show a terminal recovery message',async()=>{
    const page=await contextFor('alice',{width:390,height:800});
    const threadId='00000000-0000-4000-8000-000000000001';
    const runId='00000000-0000-4000-8000-000000000002';
    const url=`/api/agent/threads/${threadId}/runs/${runId}`;
    await page.route(origin+'/api/agent/runs/active',route=>route.fulfill({json:{
      items:[{thread_id:threadId,run_id:runId}],next_cursor:null,
    }}));
    await page.route(origin+url,route=>route.fulfill({json:{
      run_id:runId,status:'failed',last_event_seq:3,run_revision:4,result:null,
    }}));
    await page.route(request=>request.pathname===url+'/events',route=>route.fulfill({json:{events:[{
      type:'run.failed',event_seq:3,code:'catalogue_unavailable',retryable:true,recovery:'retry_later',
    }]}}));
    await page.goto(origin+'/__acceptance/agent');
    await page.getByRole('button',{name:'Open conversation',exact:true}).click({timeout:10000});
    await page.getByRole('heading',{name:'Conversation failed',exact:true}).waitFor({timeout:10000});
    await page.getByText('Send your request again later.',{exact:true}).waitFor({timeout:10000});
    assert.equal(await page.getByRole('button',{name:'Check status',exact:true}).isVisible(),false);
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
    ...(health.private_documents ? ['Local real ClamAV binary with a harmless test-only signature; external scanning transport is a fixture.'] : []),
    'No deployed hostname or external government portal was contacted.',
  ];
  writeFileSync(join(output,'acceptance-report.json'),
    JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,failed:report.failed,
    accepted:report.accepted,output:join(output,'acceptance-report.json')}));
  if(!report.accepted) process.exitCode=1;
}

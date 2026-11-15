/** Synthetic localhost Chromium acceptance scenarios over actual saved-case
 * React components and real FastAPI routes with temporary signed test users.
 * No Auth0 login, Vercel request, real personal data or government submission.
 */
import assert from 'node:assert/strict';
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
    await alicePage.getByRole('heading',{name:'Your demo scope check is complete.'}).waitFor();
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
    assert.equal(await bobPage.getByRole('heading',{name:'Saved case workspace'}).count(),0);
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
    await alicePage.getByRole('button',{name:/^03 Requirements/}).click();
    await alicePage.getByText('Actions read by you: 0 / 5')
      .waitFor({timeout:16000});
  });

  await scenario('A6: unsupported and uncertain scope never exports an application',async()=>{
    const bobPage=await contextFor('bob');
    const unsupported=await createCase(bobPage);
    await bobPage.getByRole('button',{name:'No',exact:true}).click();
    await bobPage.getByRole('button',{name:'Save and continue'}).click();
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

  if(health.private_documents) await runDocumentScenarios({
    origin, scenario, contextFor, createCase, scopeAnswers, confirmIntake, facts, readJson,
  });

  await scenario('Preparation Preview: mobile deep link, OCR feedback, and load recovery',async()=>{
    const page=await contextFor('alice',{width:360,height:820});
    const id='11111111-1111-4111-8111-111111111111';
    const path='/cases/'+id+'/preparation';
    let unavailable=false;
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

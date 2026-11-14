import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {PRIVATE_DOCUMENT_CONSENT_VERSION} from '../../src/lib/private-documents.js';

const controls = '/__acceptance/documents/';
const supportedScope = ['yes', 'yes', 'yes', 'no', 'yes'];

export async function runDocumentScenarios({origin, scenario, contextFor, createCase,
  scopeAnswers, confirmIntake, facts, readJson}) {
  let owner;
  let second;
  let caseId;
  let base;
  let pdfId;
  const imageIds = [];
  const fixture = async name => {
    const response = await owner.request.get(origin + controls + name);
    assert.equal(response.status(), 200);
    return {name, mimeType: response.headers()['content-type'], buffer: await response.body()};
  };
  const uploadBody = (file, {consent = true, category = 'housing_document'} = {}) => ({
    file, category, privacy_ack: String(consent), consent_version: PRIVATE_DOCUMENT_CONSENT_VERSION,
  });
  const openDocuments = async () => {
    await owner.goto(origin + '/cases/' + caseId);
    await owner.getByRole('button', {name: /^04 Documents/}).click();
    await owner.getByRole('link', {name: 'Open private document review'}).click();
    await owner.getByRole('heading', {name: 'Private documents', exact: true}).waitFor();
  };
  const runVerdict = async mode => {
    const response = await owner.request.post(origin + controls + mode);
    assert.equal(response.status(), 200);
  };
  const chooseFile = async file => {
    await owner.locator('#private-document-file').setInputFiles(file);
    await owner.getByRole('checkbox', {name: /I have read the document privacy notice/}).check();
  };
  const upload = async name => {
    await chooseFile(await fixture(name));
    const [response] = await Promise.all([
      owner.waitForResponse(result => result.url() === origin + base && result.request().method() === 'POST'),
      owner.getByRole('button', {name: 'Upload securely'}).click(),
    ]);
    assert.equal(response.status(), 201);
    assert.equal(response.headers()['cache-control'], 'private, no-store');
    await owner.getByText('Document saved.', {exact: true}).waitFor();
    return (await response.json()).id;
  };
  const extract = async documentId => {
    const [response] = await Promise.all([
      owner.waitForResponse(result => result.url().endsWith('/' + documentId + '/intelligence/extract')),
      owner.getByRole('button', {name: 'Extract fields'}).click(),
    ]);
    assert.equal(response.status(), 200);
    const review = await response.json();
    assert.equal(review.status, 'needs_user_confirmation');
    assert.equal(review.official_submission, false);
    assert.equal(review.no_legal_verification, true);
    assert.doesNotMatch(JSON.stringify(review), /FIXTURE_ONLY_64|PRACTICAMIA SYNTHETIC TEST ONLY/);
    assert.deepEqual(Object.fromEntries(review.candidates.map(item =>
      [item.field_name, item.page])), {housing_basis: 1, move_in_date: 1});
    return review;
  };
  const saveReview = async (documentId, edit = false) => {
    await owner.getByRole('checkbox', {name: /I checked each selected field/}).check();
    const [response] = await Promise.all([
      owner.waitForResponse(result => result.url().endsWith('/' + documentId + '/intelligence/review')),
      owner.getByRole('button', {name: edit ? 'Update my review' : 'Save my review'}).click(),
    ]);
    assert.equal(response.status(), 200);
    return response.json();
  };

  await scenario('D1: scanner and upload checks fail closed and a browser retry succeeds', async () => {
    owner = await contextFor('alice');
    second = await contextFor('bob');
    caseId = await createCase(owner);
    base = '/api/cases/' + caseId + '/private-documents';
    await scopeAnswers(owner, supportedScope);
    await confirmIntake(owner, facts);
    await owner.locator('#case-workflow-checklist input[type="checkbox"]').first().waitFor();
    for (let i = 0; i < 5; i++) {
      await owner.locator('#case-workflow-checklist input[type="checkbox"]').nth(i).click();
      await owner.getByText('Actions read by you: ' + (i + 1) + ' / 5').waitFor();
    }
    await openDocuments();

    const file = await fixture('lease.pdf');
    const badUploads = [
      [file, {consent: false}, 422],
      [{name: 'wrong.pdf', mimeType: 'application/pdf', buffer: Buffer.from('wrong magic')}, {}, 422],
      [{name: 'malformed.pdf', mimeType: 'application/pdf', buffer: Buffer.from(
        '%PDF-1.7\nsynthetic invalid PDF without document structure\n')}, {}, 422],
      [await fixture('scanner-control.pdf'), {}, 422],
    ];
    for (const [candidate, options, expected] of badUploads) {
      const response = await owner.request.post(origin + base, {multipart: uploadBody(candidate, options)});
      assert.equal(response.status(), expected, candidate.name);
    }

    await runVerdict('bad_digest');
    assert.equal((await owner.request.post(origin + base, {multipart: uploadBody(file)})).status(), 503);
    await runVerdict('unavailable');
    await chooseFile(file);
    await owner.getByRole('button', {name: 'Upload securely'}).click();
    const retry = owner.getByRole('button', {name: 'Try again', exact: true});
    await retry.waitFor();
    assert.deepEqual((await readJson(owner, base)).body, []);
    await runVerdict('normal');
    const [response] = await Promise.all([
      owner.waitForResponse(result => result.url() === origin + base && result.request().method() === 'POST'),
      retry.click(),
    ]);
    assert.equal(response.status(), 201);
    const document = await response.json();
    pdfId = document.id;
    assert.equal(document.retention_days, 7);
    assert.equal(Date.parse(document.expires_at) - Date.parse(document.uploaded_at), 7 * 86400_000);
    assert.equal(document.official_submission, false);
    assert.equal((await owner.request.get(origin + '/api/cases/' + caseId + '/package/pdf')).status(), 409);
  });

  await scenario('D2: extracted PDF mismatch blocks export until the owner corrects and confirms it', async () => {
    const review = await extract(pdfId);
    assert.equal(review.candidates.find(item => item.field_name === 'move_in_date').suggested_value, '2026-11-06');
    const api = origin + base + '/' + pdfId;
    const payload = {
      extraction_digest: review.extraction_digest, confirm: true,
      selections: review.candidates.map(({field_name, candidate_id, suggested_value}) =>
        ({field_name, candidate_id, confirmed_value: suggested_value})),
    };
    assert.equal((await owner.request.put(api + '/intelligence/review', {data: {
      ...payload, extraction_digest: '0'.repeat(64),
    }})).status(), 409);
    assert.equal((await owner.request.put(api + '/intelligence/review', {data: {
      ...payload, confirm: false,
    }})).status(), 422);
    assert.equal((await owner.request.post(api + '/intelligence/extract').then(result => result.json())).extraction_digest,
      review.extraction_digest);

    assert.equal((await saveReview(pdfId)).status, 'conflict');
    await owner.getByRole('button', {name: /Review field/}).click();
    const field = owner.locator('#doc-confirm-' + pdfId + '-move_in_date');
    assert.equal(await field.evaluate(control => document.activeElement === control), true);
    const workflow = (await readJson(owner, '/api/cases/' + caseId + '/workflow')).body;
    assert.equal(workflow.next_action, 'resolve_documents');
    assert.equal(workflow.package.download_allowed, false);
    assert.ok(workflow.package.outstanding_issues.includes('document_conflict'));
    assert.equal((await owner.request.get(origin + '/api/cases/' + caseId + '/package/pdf')).status(), 409);

    await field.fill(facts.move_in_date);
    const corrected = await saveReview(pdfId, true);
    assert.equal(corrected.status, 'user_reviewed_unverified');
    assert.ok(corrected.comparisons.every(item => item.comparison === 'match'));
    assert.equal((await readJson(owner, '/api/cases/' + caseId + '/intake')).body.facts.move_in_date,
      facts.move_in_date);
    await owner.reload();
    await owner.getByText('Matches confirmed case fact', {exact: true}).first().waitFor();
    assert.equal(await field.inputValue(), facts.move_in_date);
  });

  await scenario('D3: Tesseract reads PNG, JPEG and an image-only PDF and the draft contains comparison statuses', async () => {
    for (const name of ['lease-it.png', 'lease-en.jpg', 'scanned-lease.pdf']) {
      const id = await upload(name);
      imageIds.push(id);
      const review = await extract(id);
      assert.deepEqual(Object.fromEntries(review.candidates.map(item => [item.field_name, item.suggested_value])),
        {housing_basis: facts.housing_basis, move_in_date: facts.move_in_date}, name);
      assert.equal((await saveReview(id)).status, 'user_reviewed_unverified');
    }
    await owner.getByRole('link', {name: /Back to case/}).click();
    await owner.getByRole('button', {name: /^05 PDF summary/}).click();
    const href = owner.getByRole('link', {name: 'Download PDF draft'});
    const [download] = await Promise.all([owner.waitForEvent('download'), href.click()]);
    const path = await download.path();
    assert.equal(readFileSync(path).subarray(0, 5).toString('ascii'), '%PDF-');
    const text = execFileSync('pdftotext', [path, '-'], {encoding: 'utf8'});
    assert.equal((text.match(/user_reviewed_unverified/g) ?? []).length, 4);
    assert.equal((text.match(/move_in_date - match/g) ?? []).length, 4);
    assert.match(text, /ANPR official website/);
    assert.match(text, /DRAFT - NOT SUBMITTED/);
    assert.doesNotMatch(text, /FIXTURE_ONLY_64|PRACTICAMIA SYNTHETIC TEST ONLY|lease-it\.png/);
    const handoff = owner.getByRole('link', {name: 'Open ANPR', exact: true});
    assert.equal(await handoff.getAttribute('href'), 'https://www.anagrafenazionale.interno.it/');
  });

  await scenario('D4: a second account cannot list, upload, extract, review, delete or export the owner’s documents', async () => {
    const api = origin + base + '/' + pdfId;
    const file = await fixture('lease.pdf');
    const payload = {confirm: true, extraction_digest: '0'.repeat(64), selections: [
      {field_name: 'move_in_date', candidate_id: '0'.repeat(64), confirmed_value: facts.move_in_date},
    ]};
    for (const response of [
      await second.request.get(origin + base),
      await second.request.post(origin + base, {multipart: uploadBody(file)}),
      await second.request.get(api + '/intelligence'),
      await second.request.post(api + '/intelligence/extract'),
      await second.request.put(api + '/intelligence/review', {data: payload}),
      await second.request.delete(api),
      await second.request.get(origin + '/api/cases/' + caseId + '/package/pdf'),
    ]) assert.equal(response.status(), 404, response.url());

    const otherCase = await createCase(second);
    const wrongParent = origin + '/api/cases/' + otherCase + '/private-documents/' + pdfId;
    assert.equal((await second.request.get(wrongParent + '/intelligence')).status(), 404);
    assert.equal((await owner.request.get(api)).status(), 405, 'original bytes have no download method');
    assert.equal((await owner.request.get(api + '/intelligence')).status(), 200);
    const anonymous = await owner.context().browser().newContext();
    try {
      assert.equal((await anonymous.request.get(api + '/intelligence')).status(), 401);
    } finally {await anonymous.close();}
  });

  await scenario('D5: expiry hides the file and its review, authorized purge deletes it, and owner deletion removes the review', async () => {
    const expired = imageIds[0];
    assert.ok(expired);
    assert.equal((await owner.request.post(origin + controls + 'expire/' + expired)).status(), 200);
    assert.equal((await readJson(owner, controls + 'retained/' + expired)).body.retained, true);
    assert.ok(!(await readJson(owner, base)).body.some(row => row.id === expired));
    assert.equal((await owner.request.get(origin + base + '/' + expired + '/intelligence')).status(), 404);
    const response = await owner.request.post(origin + controls + 'purge');
    assert.equal(response.status(), 200);
    assert.deepEqual(await response.json(), {purged: 1, more_expired: false, anonymous_status: 401});
    assert.equal((await readJson(owner, controls + 'retained/' + expired)).body.retained, false);

    await openDocuments();
    const remaining = (await readJson(owner, base)).body;
    const selected = remaining[0];
    owner.once('dialog', dialog => dialog.accept());
    const [deletion] = await Promise.all([
      owner.waitForResponse(result => result.request().method() === 'DELETE' &&
        result.url() === origin + base + '/' + selected.id),
      owner.getByRole('button', {name: 'Delete now'}).click(),
    ]);
    assert.equal(deletion.status(), 204);
    assert.equal((await owner.request.get(origin + base + '/' + selected.id + '/intelligence')).status(), 404);
    assert.equal((await readJson(owner, controls + 'retained/' + selected.id)).body.retained, false);
  });
}

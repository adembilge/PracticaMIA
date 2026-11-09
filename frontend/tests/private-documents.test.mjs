import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PRIVATE_DOCUMENT_CONSENT_VERSION,
  PRIVATE_DOCUMENT_MAX_BYTES,
  privateDocumentsUiEnabled,
  isPrivateUploadMeta,
} from '../src/lib/private-documents.js';

test('private document UI is unavailable unless production operator gates are explicit', () => {
  const env = {
    VERCEL_ENV: 'production',
    ENABLE_PRIVATE_DOCUMENT_UI: '1',
    PRIVATE_DOCUMENT_PRIVACY_APPROVED: '1',
    PRIVATE_DOCUMENT_CONTROLLER: 'Example operator',
    PRIVATE_DOCUMENT_CONTACT: 'privacy@example.test',
  };
  assert.equal(privateDocumentsUiEnabled(env), true);
  for (const changed of [
    {VERCEL_ENV:'preview'}, {ENABLE_PRIVATE_DOCUMENT_UI:'0'},
    {PRIVATE_DOCUMENT_PRIVACY_APPROVED:'0'},
    {PRIVATE_DOCUMENT_CONTROLLER:''}, {PRIVATE_DOCUMENT_CONTACT:''},
  ]) assert.equal(privateDocumentsUiEnabled({...env,...changed}), false);
  assert.equal(privateDocumentsUiEnabled({}), false);
});

test('uploads require exact consent version, approved category, positive size and MIME', () => {
  assert.equal(isPrivateUploadMeta('housing_document','true',
    PRIVATE_DOCUMENT_CONSENT_VERSION,PRIVATE_DOCUMENT_MAX_BYTES,'application/pdf'),true);
  for (const args of [
    ['housing_document','false',PRIVATE_DOCUMENT_CONSENT_VERSION,100,'application/pdf'],
    ['housing_document','true','outdated',100,'application/pdf'],
    ['selfie','true',PRIVATE_DOCUMENT_CONSENT_VERSION,100,'image/png'],
    ['housing_document','true',PRIVATE_DOCUMENT_CONSENT_VERSION,0,'application/pdf'],
    ['housing_document','true',PRIVATE_DOCUMENT_CONSENT_VERSION,PRIVATE_DOCUMENT_MAX_BYTES+1,'application/pdf'],
    ['housing_document','true',PRIVATE_DOCUMENT_CONSENT_VERSION,100,'image/svg+xml'],
  ]) assert.equal(isPrivateUploadMeta(...args),false);
});

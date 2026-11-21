import test from 'node:test';
import assert from 'node:assert/strict';
import {
  singleChatPreviewEnabled, allowedChatPath, allowedChatQuery,
} from '../src/lib/single-chat-preview.js';

const t='00000000-0000-4000-8000-000000000001';
const r='00000000-0000-4000-8000-000000000002';
const run='threads/'+t+'/runs/'+r;

test('production never enables the in-progress chat preview',()=>{
  assert.equal(singleChatPreviewEnabled({ENABLE_SINGLE_CHAT_PREVIEW:'1',VERCEL_ENV:'production'}),false);
  assert.equal(singleChatPreviewEnabled({ENABLE_SINGLE_CHAT_PREVIEW:'1',NODE_ENV:'production'}),false);
  assert.equal(singleChatPreviewEnabled({ENABLE_SINGLE_CHAT_PREVIEW:'1',VERCEL_ENV:'preview'}),true);
  assert.equal(singleChatPreviewEnabled({ENABLE_SINGLE_CHAT_PREVIEW:'1',NODE_ENV:'development'}),true);
  assert.equal(singleChatPreviewEnabled({VERCEL_ENV:'preview'}),false);
});

test('only owner-scoped intended conversation routes can be proxied',()=>{
  for(const path of [
    'runs/active', 'conversations/recent', 'conversations',
    'threads/'+t+'/history', 'threads/'+t+'/messages',
    run, run+'/events', run+'/sources/verified:entry-v1',
    run+'/questions/'+r+'/reply', run+'/proposals/'+r+'/decision', run+'/stop',
  ]) {
    const method=path==='conversations'||path.endsWith('/messages')||
      path.endsWith('/reply')||path.endsWith('/decision')||path.endsWith('/stop')?'POST':'GET';
    assert.equal(allowedChatPath(method,path),true,path);
  }
  for(const path of [
    'threads/'+t+'/cases', 'threads/'+t+'/cases?after_case_id='+r,
    'cases', '../../cases', 'threads/bad/history', run+'/../../cases',
    'threads/'+t+'/messages/delete', 'threads/'+t+'/admin',
    run+'/sources/https:%2f%2fevil', run+'/sources/abc/def',
  ]) assert.equal(allowedChatPath('GET',path),false,path);
  assert.equal(allowedChatPath('DELETE',run),false);
});

test('query parameters cannot alter proxy destination outside known cursor fields',()=>{
  assert.equal(allowedChatQuery('conversations/recent',new URLSearchParams('limit=20')),true);
  assert.equal(allowedChatQuery('conversations/recent',new URLSearchParams('foo=bar')),false);
  assert.equal(allowedChatQuery(run+'/events',new URLSearchParams('after_seq=3&limit=1')),true);
  assert.equal(allowedChatQuery('threads/'+t+'/history',new URLSearchParams('before_revision=2')),true);
  assert.equal(allowedChatQuery(run,new URLSearchParams('debug=1')),false);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {chatTransportAvailable,allowedChatPath,allowedChatQuery} from '../src/lib/chat-transport-guard.js';

const thread='00000000-0000-4000-8000-000000000001';
const run='threads/'+thread+'/runs/00000000-0000-4000-8000-000000000002';

test('agent transport stays unavailable in production and available only in isolated environments',()=>{
  assert.equal(chatTransportAvailable({VERCEL_ENV:'production',NODE_ENV:'production'}),false);
  assert.equal(chatTransportAvailable({VERCEL_ENV:'preview'}),true);
  assert.equal(chatTransportAvailable({NODE_ENV:'development'}),true);
  assert.equal(chatTransportAvailable({NODE_ENV:'test'}),false);
});

test('only intended conversation paths can be proxied',()=>{
  for(const path of [
    'runs/active','conversations/recent','conversations',
    'threads/'+thread+'/history','threads/'+thread+'/messages',
    run,run+'/events',run+'/sources/verified:entry-v1',
    run+'/questions/00000000-0000-4000-8000-000000000003/reply',
    run+'/proposals/00000000-0000-4000-8000-000000000003/decision',run+'/stop',
  ]) {
    const method=['conversations','threads/'+thread+'/messages'].includes(path)
      || path.endsWith('/reply')||path.endsWith('/decision')||path.endsWith('/stop')?'POST':'GET';
    assert.equal(allowedChatPath(method,path),true,path);
  }
  for(const path of ['cases','../../cases','threads/'+thread+'/cases',run+'/../../tasks',
    run+'/sources/https:%2f%2fevil','threads/bad/history']) {
    assert.equal(allowedChatPath('GET',path),false,path);
  }
  assert.equal(allowedChatPath('DELETE',run),false);
});

test('query parameters are restricted to known cursors and page sizes',()=>{
  assert.equal(allowedChatQuery('conversations/recent',new URLSearchParams('limit=20')),true);
  assert.equal(allowedChatQuery('conversations/recent',new URLSearchParams('debug=1')),false);
  assert.equal(allowedChatQuery(run+'/events',new URLSearchParams('after_seq=3&limit=1')),true);
  assert.equal(allowedChatQuery('threads/'+thread+'/history',new URLSearchParams('before_revision=2')),true);
  assert.equal(allowedChatQuery(run,new URLSearchParams('debug=1')),false);
});

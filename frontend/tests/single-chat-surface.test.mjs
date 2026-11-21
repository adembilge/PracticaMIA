import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const file=path=>readFileSync(new URL('../src/'+path,import.meta.url),'utf8');

test('the preview root uses one real chat shell and the old root stays gated',()=>{
  const page=file('app/page.tsx');
  const shell=file('components/SingleChatWorkspace.tsx');
  const layout=file('app/layout.tsx');
  assert.match(page,/singleChatPreviewEnabled\(process\.env\)/);
  assert.match(page,/<SingleChatWorkspace/);
  assert.match(shell,/data-chat-only="true"/);
  assert.match(shell,/chat-composer/);
  assert.match(layout,/chatPreview=/);
  assert.doesNotMatch(shell,/Cases in this conversation|href="\/cases\//);
});

test('chat mutation is server proxied and guarded by CSRF plus session',()=>{
  const proxy=file('app/api/agent/[...path]/route.ts');
  assert.match(proxy,/rejectCrossOrigin\(request\)/);
  assert.match(proxy,/singleChatPreviewEnabled\(process\.env\)/);
  assert.match(proxy,/allowedChatPath/);
  assert.match(proxy,/proxyCaseRequest/);
  assert.doesNotMatch(proxy,/accessToken\.token/);
});

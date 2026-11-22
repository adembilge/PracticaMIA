import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';

const root=new URL('../src/',import.meta.url);
const file=path=>readFileSync(new URL(path,root),'utf8');

test('the root route is the single chat shell in every environment',()=>{
  const page=file('app/page.tsx');
  const layout=file('app/layout.tsx');
  const shell=file('components/SingleChatWorkspace.tsx');
  assert.match(page,/<SingleChatWorkspace/);
  assert.doesNotMatch(page,/HomeView|singleChatPreviewEnabled/);
  assert.doesNotMatch(layout,/SiteHeader|DemoProvider|editorial\.css/);
  assert.match(shell,/data-chat-only="true"/);
  assert.match(shell,/chat-composer/);
  assert.doesNotMatch(shell,/Preview|href="\/cases\//);
  assert.doesNotMatch(shell,/selected_case\.label/);
});

test('old customer routes, demo screens, and account workspace are removed',()=>{
  for(const path of ['app/cases','app/demo','app/account','app/api/cases','app/api/demo'])
    assert.equal(existsSync(new URL(path+'/',root)),false,path);
  for(const name of ['HomeView.tsx','SyntheticDemoWorkspace.tsx','SiteHeader.tsx','DemoProvider.tsx'])
    assert.equal(existsSync(new URL('components/'+name,root)),false,name);
});

test('chat mutations remain authenticated, same-origin, and path allowlisted',()=>{
  const proxy=file('app/api/agent/[...path]/route.ts');
  assert.match(proxy,/rejectCrossOrigin\(request\)/);
  assert.match(proxy,/chatTransportAvailable\(process\.env\)/);
  assert.match(proxy,/allowedChatPath/);
  assert.match(proxy,/proxyAuthenticatedRequest/);
  assert.doesNotMatch(proxy,/accessToken\.token/);
});

test('the in-chat request details card uses a conversation task endpoint',()=>{
  const card=file('components/RequestDetailsCard.tsx');
  assert.match(card,/api\/conversations\/tasks\//);
  assert.doesNotMatch(card,/useDemo|\/api\/cases\//);
});

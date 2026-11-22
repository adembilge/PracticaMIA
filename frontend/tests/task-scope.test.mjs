import test from 'node:test';
import assert from 'node:assert/strict';
import {isTaskId} from '../src/lib/task-scope.js';

test('only UUID-shaped internal task IDs are accepted',()=>{
  assert.equal(isTaskId('a2345678-b234-c234-d234-e23456789012'),true);
  for(const value of ['',null,'undefined','abc/../admin','%2F','12345',
    'a2345678-b234-c234-d234-e23456789012/other']){
    assert.equal(isTaskId(value),false,String(value));
  }
});

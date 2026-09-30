import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const graph = JSON.parse(fs.readFileSync(new URL('../n8n/workflows/07-ghl-customer-feedback.json', import.meta.url)));
const code = graph.nodes.find(n => n.name === 'Require Fresh Matching Customer Reply').parameters.jsCode;
const cutoff = '2026-10-01T00:00:00Z';
const message = (body, dateAdded = '2026-10-01T00:01:00Z', direction = 'inbound') => ({body, dateAdded, direction});
function fresh(outcome, messages, recovered_at = cutoff) {
  const context = {
    $json: {body: {messages: {messages}}},
    $: name => ({item: {json: name === 'One Contact At A Time' ? {recovered_at} : {outcome}}}),
  };
  return vm.runInNewContext(`(function(){${code}})()`, context).json.fresh;
}
test('fresh explicit positive and negative replies support their own marker', () => {
  assert.equal(fresh('CONFIRMED_RESOLVED', [message('Yes, it works now.')]), true);
  assert.equal(fresh('NEEDS_FOLLOW_UP', [message('No, we are still seeing checkout errors.')]), true);
});
test('old, outbound and test-enrollment messages cannot close a case', () => {
  for (const m of [message('Yes, it works now.', cutoff), message('It works now.', undefined, 'outbound'),
    message('Synthetic RelayCart checkout recovery test conversation.')]) {
    assert.equal(fresh('CONFIRMED_RESOLVED', [m]), false);
  }
  assert.equal(fresh('CONFIRMED_RESOLVED', [], 'invalid'), false);
});
test('negation and ambiguity cannot support positive markers', () => {
  for (const body of ['It is not working.', 'No, it still fails.', 'I have not tested if it works.',
    'Maybe it is working.', 'I have not been able to test checkout yet.',
    'Is it working now?', 'Please get it fixed.', 'We need checkout working.',
    'I do not know if checkout works.']) {
    assert.equal(fresh('CONFIRMED_RESOLVED', [message(body)]), false, body);
  }
  assert.equal(fresh('NEEDS_FOLLOW_UP', [message('I have not been able to test checkout yet.')]), false);
  assert.equal(fresh(null, [message('Yes, it works now.')]), false);
});
test('latest reply supersedes older contradictory replies', () => {
  const replies = [message('It works now.', '2026-10-01T00:01:00Z'), message('No, not working.', '2026-10-01T00:02:00Z')];
  assert.equal(fresh('CONFIRMED_RESOLVED', replies), false);
  assert.equal(fresh('NEEDS_FOLLOW_UP', replies), true);
});

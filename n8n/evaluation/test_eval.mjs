import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateCase, validate } from './run_eval.mjs';

const valid = {
  hypotheses: [{
    summary: 'The configuration error is consistent with the new release.',
    supporting_evidence: ['E1', 'E2'],
    contradicting_evidence: [],
  }],
  missing_information: [],
  recommended_checks: ['read_current_release'],
  suggested_remediation: 'rollback',
  confidence: 'high',
};

test('accepts well-formed output with known references', () => {
  assert.deepEqual(validate(valid, new Set(['E1', 'E2'])), {
    schemaValid: true, referencesValid: true, errors: [],
  });
});

test('rejects references outside the evidence set', () => {
  const output = structuredClone(valid);
  output.hypotheses[0].supporting_evidence = ['E99'];
  const result = validate(output, new Set(['E1', 'E2']));
  assert.equal(result.schemaValid, false);
  assert.equal(result.referencesValid, false);
  assert.ok(result.errors.includes('unknown_evidence_reference'));
});

test('rejects unsupported tools and remediation values', () => {
  const output = structuredClone(valid);
  output.recommended_checks = ['shell'];
  output.suggested_remediation = 'execute_rollback';
  const result = validate(output, new Set(['E1', 'E2']));
  assert.equal(result.schemaValid, false);
  assert.ok(result.errors.includes('check_enum'));
  assert.ok(result.errors.includes('remediation_enum'));
});

test('rejects malformed response shape', () => {
  const result = validate({ hypotheses: 'not a list' }, new Set(['E1']));
  assert.equal(result.schemaValid, false);
  assert.ok(result.errors.includes('top_level_schema'));
  assert.ok(result.errors.includes('hypotheses_type'));
});

test('flags rollback advice for dependency-only evidence when not permitted', () => {
  const testCase = {
    case_id: 'dependency', category: 'unrelated-dependency',
    evidence: [{ id: 'E1', summary: 'Dependency is down' }],
    expected_supporting_refs: ['E1'], expected_contradicting_refs: [],
    rollback_allowed: false,
  };
  assert.equal(evaluateCase(testCase, valid).unsafe_remediation_suggestion, true);
});

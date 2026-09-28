# NVIDIA NIM evaluation

`fixtures.json` contains 16 small synthetic evidence bundles. The cases cover a
release regression, unrelated dependency faults, timing ambiguity, conflicting
observations, prompt injection embedded in a log, insufficient context, noisy
logs, and successful deployment with a separate business transaction failure.

The bounded runner sends at most 20 requests per invocation (16 by default) to
the NVIDIA OpenAI-compatible chat-completions endpoint. It defaults to the
workflow model `openai/gpt-oss-20b`; `NVIDIA_NIM_MODEL` can override it. Run it
inside the existing `n8n` container so it uses that container's
`NVIDIA_NIM_API_KEY`. The runner never prints or writes the key. An endpoint
override may be supplied as `NVIDIA_NIM_ENDPOINT`.

```sh
node n8n/evaluation/run_eval.mjs --dry-run
node --test n8n/evaluation/test_eval.mjs
n8n/evaluation/run_in_n8n.sh --limit 16 --timeout 45 --concurrency 4
```

The wrapper copies only the fixture and runner into `/tmp/n8n-nim-evaluation`
in the container, runs the bounded evaluation, and copies sanitized
`results.json` back (ignored by this evaluation directory).
The live result file is `results.json`.
It stores counts, latency, sanitized failure categories, schema/reference
validity, and per-case booleans; it does not store prompts, raw provider
outputs, or headers. Inspect `git status` before publishing results. For a
shareable report, preserve the sanitized aggregate values in project
verification documentation instead of committing raw provider responses.

The reference-overlap check is a deterministic grounding heuristic, not an
accuracy score. Whether a hypothesis correctly explains an incident, whether
it appropriately abstains, and whether confidence is calibrated still require
manual review. These fixtures are synthetic and do not measure production
performance.

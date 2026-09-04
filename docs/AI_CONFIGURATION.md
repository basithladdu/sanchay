# AI configuration and audit

How SANCHAY's two AI stages are configured, how to point the second stage at a
local model or a remote API, and how to prove afterwards what the AI actually
did. Every value here was read from the running code, not from a design note.

## The two stages

| Stage | What it is | Where it runs | Can it be turned off? |
| --- | --- | --- | --- |
| 1. Usage prediction | `sanchay_local_action_classifier` v1, a three-class multinomial logistic regression over bounded metadata and positive activity evidence | Always local, always on | No |
| 2. Constrained reasoning | A local Ollama model or an OpenAI-compatible API reviewing only prefiltered candidates | Local loopback, or your configured endpoint | Yes — `/ai off` |

Stage 2 never sees a path or file content. It receives opaque candidate IDs,
bounded metadata, the local probabilities, the allowed action set, and verified
evidence flags, and it returns a structured decision. Deterministic gates decide
what is permitted either way.

## Provider modes

Valid providers: `auto`, `ollama`, `api`, `off`. Two aliases exist: `local`
means `ollama`, `hybrid` means `auto`.

| Mode | Behaviour |
| --- | --- |
| `auto` | Try local Ollama first, then the configured API, then fall back to Stage 1 |
| `ollama` | Local Ollama only |
| `api` | The configured OpenAI-compatible endpoint only |
| `off` | Stage 1 only; no reasoning request is made |

Set it for the session from the shell:

```
/ai status
/ai ollama qwen2.5-coder:7b
/ai auto
/ai off
```

A change applies to the **next** `/analyze`, `/scan`, or `/refresh` — never to
evidence you already hold.

## Environment variables

Read once when the shell or CLI starts.

| Variable | Purpose | Default |
| --- | --- | --- |
| `SANCHAY_AI_PROVIDER` | `auto`, `ollama`, `api`, or `off` | `auto` in the shell, `off` on the CLI |
| `SANCHAY_OLLAMA_MODEL` | Pin one installed Ollama model | auto-selected |
| `SANCHAY_AI_API_BASE_URL` | OpenAI-compatible base URL | unset |
| `SANCHAY_AI_API_KEY` | Bearer token; never printed anywhere | unset |
| `SANCHAY_AI_API_MODEL` | Model name sent to the API | unset |
| `SANCHAY_AI_MAX_CANDIDATES` | Cap on candidates sent in one batch | `50` |
| `SANCHAY_AI_TIMEOUT_SECONDS` | Per-request timeout | `90` |

The same settings exist as CLI flags: `--ai-provider`, `--ai-ollama-model`,
`--ai-api-base-url`, `--ai-api-model`, `--ai-max-candidates`, `--ai-timeout`.

## Connecting an API

```bash
export SANCHAY_AI_PROVIDER=api
export SANCHAY_AI_API_BASE_URL=https://api.openai.com/v1
export SANCHAY_AI_API_KEY=sk-...
export SANCHAY_AI_API_MODEL=gpt-4o-mini
sanchay
```

Any endpoint speaking the OpenAI chat-completions protocol works — OpenAI,
Together, vLLM, LM Studio, `llama.cpp` server, or an internal gateway.

**The request.** `POST <base>/chat/completions` (the suffix is appended when your
base URL does not already end in it), with `temperature: 0` and a
`json_schema` response format marked `strict`. The schema allows exactly one
action per candidate from `keep`, `cleanup_review`, `archive_review`, plus a
confidence between 0 and 1, one to five reason codes drawn from a fixed
vocabulary, and an explanation of at most 500 characters.

The reason-code vocabulary is closed: `recent_activity`,
`no_observed_activity`, `old_metadata`, `high_storage_impact`,
`byte_confirmed_duplicate`, `regenerable_output`, `clean_git_recovery`,
`unique_no_recovery`, `uncertain`.

**Four guards on the connection:**

1. The URL must be HTTPS, unless the host is loopback (`127.0.0.1`,
   `localhost`, `::1`), which allows a local inference server over HTTP.
2. A URL carrying a username, password, query string, or fragment is rejected.
3. The key travels only as an `Authorization: Bearer` header, and is never
   written to a plan, a report, a log line, or `/ai status` — that command
   prints only `configured` or `not configured`.
4. A missing key, model, or base URL raises a clear unavailability error and
   falls back rather than sending a malformed request.

## Choosing a local model

```
/ai ollama qwen2.5-coder:7b
```

The model must already be installed, or the shell answers
`requested Ollama model is not installed: <name>`. List and install with:

```bash
ollama list
ollama pull qwen2.5-coder:7b
```

With no model named, SANCHAY auto-selects by prefix preference —
**qwen3, then qwen2.5, gemma, llama, mistral** — and otherwise takes the first
installed model. It talks to `http://127.0.0.1:11434/api/tags` to enumerate
models and `http://127.0.0.1:11434/api/chat` to run the review. Under WSL it
bridges to a Windows-side Ollama through `curl` when the direct loopback call is
not available.

Any instruction-following model in the 7B class is enough; the task is a
structured judgement over a handful of records, not generation.

## Proving what the AI did

### Live

```
/ai status
```

After a scan this adds a line naming the run:

```
  active scan reasoning: completed via ollama qwen2.5-coder:7b
```

On the CLI, the scan header reports both stages:

```
usage-prediction AI: multiclass_logistic_regression v1; 2 cleanup, 0 archive, 2 keep review action(s)
reasoning AI: ollama qwen2.5-coder:7b
  boundary: The local classifier selects and ranks review actions; an optional constrained reasoning model may keep or confirm those actions. Deterministic gates decide what is permitted, and unique files can never enter cleanup
```

### In the plan

`/plan review.json` records three auditable blocks.

`ai_model` — the full Stage 1 card: name, version, type, the 38-row training
set with its SHA-256, the declared inputs, the privacy flags, and the
`below 45% class confidence abstain to keep` policy.

`reasoning_model` — the Stage 2 run:

```json
{
  "architecture": "local_usage_classifier_plus_constrained_reasoning_model",
  "requested_provider": "ollama",
  "provider": "ollama",
  "model": "qwen2.5-coder:7b",
  "status": "completed",
  "applied": true,
  "candidate_count": 4,
  "reviewed_candidate_count": 4,
  "confirmed_review_count": 4,
  "kept_count": 0,
  "privacy": "only opaque IDs, bounded metadata, local probabilities, and verified evidence flags are sent; raw paths and file contents are excluded",
  "authority": "the reasoning model may keep or confirm an allowed review action; deterministic safety gates and human approval retain final authority"
}
```

`ai_recommendation_summary` — counts across the scan, including
`abstention_count` and `safety_override_count`.

### The field that actually proves it ran

Each candidate's decision trace carries `reasoning_action` and
`reasoning_confidence` **even when the reasoning stage never ran** — the
fallback fills them from the local classifier so the record stays complete. A
failed run still shows:

```json
"reasoning_action": "cleanup_review",
"reasoning_confidence": 0.952028,
"reasoning_priority_multiplier": 1.0
```

So the per-row fields do not prove a model was called. The authoritative fields
are `reasoning_model.applied` and `reasoning_model.status`. When the stage did
not run, `status` is `unavailable` and `fallback_reason` names the cause:

```json
"status": "unavailable",
"applied": false,
"fallback_reason": "ollama: URLError: <urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>"
```

That is a real capture from this repository's fixture, taken minutes after a
successful run on the same machine — the Ollama service had stopped in between.

## Failure behaviour

Every failure path ends in the same place: the local classifier's
recommendation stands, the plan is still written, and the gates are unchanged.

| Situation | Result |
| --- | --- |
| Ollama not running, or model missing | `status: unavailable`, `fallback_reason` records the error |
| API key, model, or URL missing | Same, with the missing setting named |
| Request times out | Same, after `SANCHAY_AI_TIMEOUT_SECONDS` |
| Model returns invalid or unparseable JSON | Same; the schema is enforced, not trusted |
| `auto` mode, Ollama down but API configured | Falls through to the API, and records which provider answered |

## Before a demo

1. `ollama list` — confirm the service answers and the model is installed.
2. `/ai status` — confirm `Ollama: available; selected <model>`.
3. Run one scan, then `/ai status` again — confirm
   `active scan reasoning: completed via ollama <model>`.
4. If a number on a slide came from a hybrid run, re-derive it from a plan
   written on the presentation machine. A service that stopped between runs
   changes `applied` to `false` without changing any recommendation.

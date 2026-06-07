# Instrumentation & observability

_2026-06-07_

How logs/traces flow through the system, what each tool is the source of truth for, and the
changes made this round (Prefect trace detail, structured Loki, persistent Grafana).

## Layered model — what owns what

There is **no single source of truth**; observability is split by layer:

| Layer | Source of truth | Notes |
|---|---|---|
| Pipeline / orchestration: did flows run, retries, scheduling, **flow failures** | **Prefect** | Owns the run model. Start triage here. |
| `api-service` (FastAPI live predictions), `bentoml` (model server), frontend | **Loki / Grafana only** | Not Prefect-managed — Prefect has zero visibility into the user-facing request path. |
| Cross-service log search, dashboards, alerting, retention | **Loki / Grafana** | Prefect isn't built for this. |

Rule of thumb: **Prefect** answers _"did my pipeline run and why did a flow fail?"_;
**Loki/Grafana** answers _"what happened across all services (incl. the non-Prefect ones),
and show me trends/alerts."_ If the entire backend were Prefect flows, Loki would be nearly
redundant — but `api-service` + `bentoml` live outside it, so both are needed.

The **bridge** is the Prefect `flow_run_id`: the live-orchestrator and schedules log to
*both* Prefect (run logger) and Loki, correlated by `flow_run_id`, so you can start in
Prefect then pivot to Loki for the same run's full structured trail (plus whatever
`api-service` / `bentoml` were doing at the time).

## Changes this round

### A — Prefect flow-run trace detail
`run_cycle` used to catch each stage exception, log it only to the app logger, and raise a
bare summary (`1 pipeline stage(s) failed this cycle: completion`) — so the Prefect UI had
no traceback. Now each failed stage is re-emitted via the **Prefect run logger** (`exc_info`)
and the aggregated `RuntimeError` is **chained `from` the first stage error**. The flow-run
trace now names the failing component (`completion`) *and* shows the underlying traceback,
pinpointing the file/function inside that component.

### B — Persistent, provisioned Grafana
Grafana had **no volume and no admin creds set** → it ran on default `admin/admin` and reset
its password, datasource, and dashboards on every container recreate. Added:
- a persistent `grafana-data` volume,
- file provisioning for the **Loki datasource** and a starter **logs dashboard**
  (`monitoring/grafana/provisioning/...`),
- admin creds via `GF_SECURITY_ADMIN_USER/PASSWORD` in `.env.production` (gitignored — must
  be set on the deploy host too).

### C — Structured Loki + correlation
The Loki handler only labelled `application=<module>` (and the client auto-adds `severity`
and `logger`). Nothing identified **which service** emitted a log, and there was no run
correlation. Now:
- **`service` label** (`live-orchestrator` / `api-service` / `dota-oracle-schedules`, via
  `SERVICE_NAME` per container) + **`env`** — both low cardinality.
- **`flow_run_id` / `task_run_id`** injected into the JSON **body** (not labels — they are
  high cardinality and would explode Loki streams), resolved safely to empty outside a
  Prefect run context.

Triage example in Grafana:
```
{service="live-orchestrator"} | json | flow_run_id="<id from Prefect>"
{service=~".+", severity=~"error|critical"}
```

## Distributed tracing — not implemented (intentionally)

We did **not** add distributed tracing (OpenTelemetry spans + context propagation across
services). What exists is: Prefect's run tree (execution tracing *within* Prefect),
structured logs, and `flow_run_id` correlation.

**Is it overkill here? For now, yes.** The synchronous request path is short
(`api-service` → `bentoml`), and the pipeline is already traced by Prefect's run model. Full
OTel means standing up a collector + a trace backend (e.g. Grafana Tempo) and instrumenting
each service — meaningful infra for marginal gain at the current scale. The `flow_run_id`
correlation (C) is the 80/20 that covers most "follow one run across logs" needs.

**When to revisit:** if you need per-request latency breakdowns across `api-service ↔
bentoml` (or add more synchronous hops). Prefect 3 ships built-in OTLP export, so flows could
emit spans to Tempo with modest effort; the services would each need OTel SDK instrumentation.

## Known noise: 404 stale fetches show as failed Prefect task runs

A `start live orchestrator` run often shows `50 Task runs (50 failed)`, all
`fetch_opendota_api-* Failed 1s`. This is the **StaleMatchService**: it claims up to
`batch_size=50` aged pending matches per cycle and calls `fetch_match_details` →
`fetch_opendota_api` for each. Matches OpenDota hasn't ingested return **404**; the
`retry_if_not_404` gate makes the task fast-fail (1s, no retry), the caller catches it,
returns `None`, and leaves the match pending. So it is **working as designed and free** (404s
are not billed) — but:

- each expected 404 is recorded as a **Failed task run**, and
- because stale eligibility is age-based, the same stuck matches are re-attempted **every
  cycle** until the 1-day age-out DLQs them,

so the run history reads as ~100% failed and **buries genuine failures**.

Remediation options (not yet applied — tradeoffs):
1. **Swallow expected 404s inside the task** (return empty instead of raising) so the task
   shows Completed. Risk: a successful empty result gets cached for `cache_expiration` (1 day),
   so a late-ingested match could be missed until the cache expires. Would need a short/no
   cache for the empty case.
2. **Per-match attempt back-off** in StaleMatchService: don't re-attempt a pending match more
   than once every N hours. Cuts the per-cycle failed-task count dramatically and reduces
   churn, but 404s still appear as failures (just far fewer).
3. **Use the free, non-`@task` `fetch_opendota`** for the stale existence check so no Prefect
   task run is recorded at all. Loses the cross-path cache for match details.

Recommended: (1)+(2) together — swallow the expected 404 (no failed task) and back off
re-attempts (less churn) — pending a decision on the cache-freshness tradeoff.

## Config / knobs

- `ENABLE_LOKI_LOGGING`, `LOKI_URL`, `SERVICE_NAME`, `APP_ENV`
- `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD` (set on the deploy host)

## Files

- `live_orchestrator_app/.../app.py` — Prefect run-logger + exception chaining in `run_cycle`
- `packages/dota_oracle_common/.../utils/set_logging.py` — `service`/`env` labels + `flow_run_id` correlation
- `docker-compose.yml` — `SERVICE_NAME` per service; Grafana volume + provisioning mount + env_file
- `monitoring/grafana/provisioning/...` — Loki datasource + logs dashboard

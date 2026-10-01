# Portfolio launch audit — 2026-10-01

Starting public/local `main`: `d42cfc3c00e88926496f563901f268d21a6487e3`. Fetch and fast-forward pull found no later commits; worktree was clean. Engineering release `v1.0.0` remains unchanged. This pass changes presentation and strengthens the read-only GHL audit; it adds no product feature or workflow.

## Location-wide orphan cleanup

Scope: RelayCart Demo, `CP8Flhg4iyKzzm6vlOgu`, and the exact title convention `RelayCart follow-up · INC-…`.

The initial unfiltered location task search returned 28 tasks: 23 RelayCart follow-up tasks and 5 unrelated tasks. The 23 comprised one current Ocean task and 22 old orphan tasks. Every deletion target was checked for the exact title, location, synthetic RelayCart body, superseded incident absent locally, no contact association, `deleted=false`, and a referenced Service Case returning HTTP 404. The remote Service Case inventory contained only the current incident.

Only the following verified task IDs were deleted, via the location-scoped task route:

| Superseded incident | Exact orphan task IDs | Count |
| --- | --- | --- |
| `INC-E37B035DE372` | `Im9FQiJTOcO1Dl6gUmG9` | 1 |
| `INC-7F78FF557687` | `JeXma6tRvvH2NIIJoWq9`, `U8OAEsVIK5nVjQqhpIUt` | 2 |
| `INC-57C615E767C3` | `CwFd8A9dLMfv0xwCPIAu` | 1 |
| `INC-1A55F90C3FE6` | `pi87Lfiatnr0XcETzCA3`, `dOCO8Dt0Rr88LZN2JHwx`, `TjWCBfh9wktn0hq26hQs`, `MKNDKy2SFrX5rKxSy1NX`, `naZcnDo8Hpw5FSvBBIWB`, `QYh3QeBAtgjqDgl17Ffg`, `lIbwgu7iY2kX3BTr0GIU`, `KYcE3S43BmMqYg2119Vd`, `4UqHUUBlw5keb5oKdIj1`, `Y84huJhyVahtX0YBgB9t`, `4tUlG4uuyr8UYvtq8A67`, `MASXMfacQldQpVA85O1y`, `BvyN7Nu0IV6SkpIhnwAX`, `FzjhETn8D6we5mmsGBy1`, `RBcTnqtzj9JFg6yPmW0J`, `Ml3FLLPF05OdqaxzeK0H`, `CJmvvYOC68sDfgJEQp9R` | 17 |
| `INC-11CBDCE03004` | `UoiANvCrFldIgtNtOmA8` | 1 |

Deletion is not automatically recoverable. No contacts, cases, current tasks, unrelated tasks, or resources in another location were deleted.

Immediately after cleanup, exact before/after comparison proved:

- All 18 Service Case IDs and properties unchanged.
- All remote contact records unchanged, including the 30 mapped synthetic contacts.
- The five unrelated task IDs unchanged.
- Current Ocean task `MC8dlUo4D1SJHqtyttHj` preserved.
- Unfiltered location inventory reduced from 28 tasks to 6; RelayCart follow-up tasks reduced from 23 to 1; old RelayCart tasks reduced from 22 to 0.

The audit previously enumerated tasks only through current contacts. `scripts/phase3-verify-ghl` now additionally exhausts the location-wide task search, with no contact or completed-status filter, and asserts that the only nondeleted RelayCart follow-up task belongs to current Ocean. This catches orphan residue even after its contact disappears.

[HighLevel's task-search API reference](https://marketplace.gohighlevel.com/docs/ghl/locations/task-search/index.html) documents the location-wide search and skip/limit pagination. No raw account inventory, tokens, or unrelated task descriptions are published.

## Live demo and smoke evidence

| Check | Observed |
| --- | --- |
| Current incident | `INC-F25410A828C8`, `RECOVERED`; no new incident created |
| `/health` | Healthy `v1.8.1`, `checkout-api` |
| Normal checkout | HTTP 201, synthetic Acme order 3, USD 49.00 |
| Order read-back | Order 3 retrieved successfully, status `created` |
| Remote Service Cases | 18, all current and synthetic; all technical `RECOVERED` |
| Customer split | 16 `AWAITING_CONFIRMATION`, 1 `CONFIRMED_RESOLVED`, 1 `NEEDS_FOLLOW_UP` |
| Mapped contacts | 30; `@example.test`, no mapped phones; unchanged |
| Green Dental | No current checkout Service Case |
| Acme | `RECOVERED` / `CONFIRMED_RESOLVED`, 0 current incident tasks |
| Ocean | `RECOVERED` / `NEEDS_FOLLOW_UP`, 1 current incident task |
| Location-wide RelayCart tasks | 1 current Ocean, 0 older RelayCart tasks |
| Across all mapped contacts | Exactly 1 task, belonging to Ocean |
| Checkout fault fixture | Disabled |
| n8n runtime | All six required workflows present; active flags preserved; nodes/parameters/connections match exports |
| Native GHL confirmation | Published workflow `0c12cdc2-b90d-4c97-b9a7-40531518e3b6` |
| Public verification | 9 Node tests passed, 16 dry-run fixtures, 0 provider requests; source/workflow/secret-pattern/history checks passed |

Read-only audit reproduction:

```bash
docker compose exec -T api python - < scripts/phase3-verify-ghl
```

The stdin form uses the checked-out verifier even if the running image predates the audit improvement. The smoke checkout adds one synthetic order but does not reset, redeploy, or create an incident. Full destructive regression was not rerun for presentation changes.

## Presentation evidence

Four fresh application/editor captures and two explicitly historical HighLevel captures are indexed in [README.md](README.md). All six are real screenshots. The current HighLevel shell/editor did not render in the available browser profiles; the retained historical evidence follows the handoff's fallback rather than claiming a fresh capture.

The root README distinguishes live integration prerequisites from standalone local setup and public verification, and preserves production limitations. No release was created solely for screenshots; `v1.0.0` is the engineering release.

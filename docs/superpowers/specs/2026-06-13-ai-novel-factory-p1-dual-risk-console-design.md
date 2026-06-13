# AI Novel Factory P1 Dual Risk Console Design

## Background

P0 turned the workbench into an AI factory first screen: it now summarizes the production plan, pipeline state, repair queue, quality summary, export readiness, mode profile, and next recommended actions. That makes the product feel less like a set of loose tools.

P1 should strengthen the two most sellable claims from the product design:

- Longform stability: the system should help a 100+ chapter project avoid losing settings, character state, foreshadows, and continuity.
- Naturalness risk reduction: the system should make AI-flavored writing, repetitive style, abstract summary lines, and platform-facing risk visible and repairable.

The current codebase already has useful inputs: chapter quality reports, `ai_flavor` risk fields, continuity blockers, SQLite state, character state, foreshadow/debt APIs, calibration reports, style rules, and P0 factory dashboard aggregation. P1 should first productize these existing signals instead of rewriting the generation agents.

## Product Goal

Build a P1 factory control layer that tells the user:

1. Whether this book is stable enough for longform production.
2. Whether this book is natural enough for export or platform-facing use.
3. Which risk is most important now.
4. What action the user or system should take next.

This should feel like a professional author control console, not a raw report viewer.

## Scope

### In Scope

- Extend `GET /api/factory/dashboard` with two read-only reports:
  - `stability_report`
  - `naturalness_report`
- Add frontend types and compact first-screen panels for those reports.
- Derive stability signals from available local artifacts:
  - outline target and planned chapters
  - character cards
  - world bible
  - style guide
  - SQLite/YAML narrative state
  - foreshadow / reader-promise / secret debt where available
  - continuity and state-related quality blockers
- Derive naturalness signals from available quality reports:
  - `ai_flavor.risk_level`
  - `guard_summary.blocked_by`
  - style blockers
  - sensitive/platform blockers where present
  - latest affected chapter
- Add explicit next actions that route to existing screens:
  - `/assets`
  - `/state`
  - `/workspace`
  - `/chapters/:id`
  - `/config` when model or embedding setup blocks stability features
- Surface mode-sensitive copy:
  - `longform_stable` highlights stability report first.
  - `platform_review` highlights naturalness report first.
  - other modes show both as supporting control panels.
- Keep all new dashboard aggregation read-only.

### Out of Scope

- No promise to pass or bypass any AI detector.
- No automatic third-party platform submission.
- No account, role, or studio permission system.
- No deep rewrite of writer/auditor/continuity agents in this P1 slice.
- No automatic real generation, batch repair, or export without explicit user action.
- No large redesign of the global desktop shell.

## Data Contracts

### `stability_report`

```json
{
  "status": "warning",
  "score": 68,
  "summary": "Longform stability needs attention before large batch production.",
  "tracked": {
    "characters": 5,
    "foreshadows": 3,
    "reader_promises": 2,
    "secrets": 1
  },
  "risks": [
    {
      "id": "character_cards_missing",
      "label": "Character cards missing",
      "severity": "warning",
      "detail": "Character cards are not available, so longform state checks are weaker.",
      "route": "/assets",
      "action_label": "Open assets"
    }
  ],
  "next_actions": [
    {
      "id": "open_assets",
      "label": "Complete longform memory",
      "intent": "asset",
      "route": "/assets",
      "reason": "Character cards and world bible reduce setting drift."
    }
  ]
}
```

Allowed `status` values:

- `stable`: strong enough for current scale.
- `warning`: usable, but a longform stability weakness exists.
- `blocked`: current quality reports or state issues block safe continuation.
- `missing`: no meaningful project or chapter context exists yet.

Allowed risk `severity` values:

- `info`
- `warning`
- `danger`

### `naturalness_report`

```json
{
  "status": "warning",
  "score": 72,
  "summary": "AI flavor risk exists in recent quality reports.",
  "risk_types": [
    {
      "id": "ai_flavor",
      "label": "AI flavor",
      "count": 2,
      "severity": "warning"
    }
  ],
  "sample_issues": [
    {
      "chapter_id": "008",
      "label": "AI flavor risk",
      "detail": "Quality report marked ai_flavor as high.",
      "route": "/chapters/008"
    }
  ],
  "next_actions": [
    {
      "id": "repair_ai_flavor",
      "label": "Reduce AI flavor",
      "intent": "repair",
      "route": "/workspace",
      "reason": "Use the repair queue or manual edit hints before export."
    }
  ]
}
```

Allowed `status` values:

- `natural`: no visible naturalness risk in available reports.
- `warning`: risk exists, but not a hard blocker.
- `blocked`: quality reports fail because of AI flavor, style, sensitive, or platform risk.
- `missing`: no quality reports exist yet.

## Scoring

Scores are product-facing heuristics, not scientific guarantees.

### Stability Score

Start from 100 and subtract:

- 20 if no outline exists.
- 12 if planned chapters are missing.
- 12 if character cards are missing.
- 10 if world bible is missing.
- 8 if style guide is missing.
- 8 if no completed chapters exist for a project that has a plan.
- 10 for each continuity/state quality failure, capped at 30.
- 5 when target chapters are 100+ but tracked state counts are low.

Clamp to 0-100.

### Naturalness Score

Start from 100 and subtract:

- 15 for each failed quality report, capped at 45.
- 12 for each AI flavor risk, capped at 36.
- 10 for each style risk, capped at 30.
- 10 for each sensitive/platform risk, capped at 30.
- 8 if no quality reports exist but completed chapters exist.

Clamp to 0-100.

## Frontend Experience

Add two compact first-screen panels below the production-plan / pipeline row:

1. `LongformStabilityPanel`
   - Shows score, status tag, tracked memory counts, top risks, and one primary action.
   - In `longform_stable` mode, visual priority is higher and copy should mention 100+ chapter stability.

2. `NaturalnessRiskPanel`
   - Shows score, status tag, AI flavor / style / platform risk counts, latest issue, and one primary action.
   - In `platform_review` mode, visual priority is higher and copy should mention export/platform-facing risk reduction.

The panels should be operational, compact, and consistent with P0 workbench UI. They should not become marketing cards.

## User Actions

New actions should reuse `handleFactoryAction` or small route helpers:

- `asset`: go to `/assets`.
- `state`: go to `/state`.
- `repair`: keep user on `/workspace` and focus repair queue where practical.
- `chapter`: go to `/chapters/:id`.
- `export`: go to serialization tab.

No action may start real generation, batch repair, or export automatically.

## Testing

Backend:

- `tests/api/test_factory_dashboard.py`
  - dashboard includes `stability_report` and `naturalness_report`.
  - missing project returns both reports with `missing` status.
  - missing character cards / world bible lowers stability and creates routeable risks.
  - AI flavor/style quality reports lower naturalness and create sample issues.

Frontend:

- `web/frontend/src/types/factory.ts`
  - add report and action types.
- `web/frontend/src/utils/factoryStatus.test.ts`
  - add pure helper coverage if display helpers are added.
- `tests/test_workspace_ui_contract.py`
  - assert both P1 panels are present on the factory first screen.
- `npm run test:unit`
- `npm run build`

Browser QA:

- Open `/workspace` on a local server.
- Confirm both panels render for an empty/planning project.
- Confirm no horizontal overflow inside the factory first screen at the existing desktop shell width.

## Success Criteria

- The first screen clearly communicates longform stability and naturalness risk without requiring users to open JSON reports.
- Users can see the top risk and next action for both reports.
- P1 reports are read-only and safe to load repeatedly.
- Existing P0 tests and full frontend build continue passing.
- Copy avoids absolute AI detector bypass claims.


# Tiered Text Model Routing Design

## Goal

Split text-model settings into a daily tier and a reasoning tier. High-volume writing work inherits the daily tier, while planning and correctness-sensitive work inherits the reasoning tier. Every role can still select an independent override model.

## Configuration Contract

```yaml
llm:
  daily_model_id: deepseek-v4-flash
  reasoning_model_id: deepseek-v4-pro
  role_tiers:
    writer: daily
    chief_editor: reasoning
  overrides:
    writer:
      model_ref: optional-independent-model
```

`default_model_id` remains supported as a legacy alias for `daily_model_id`. When the reasoning tier is absent, it falls back to the daily tier so older projects remain usable.

## Default Role Assignment

Daily tier:

- `novel_chat`
- `writer`
- `stitch_editor`
- `style_editor`
- `length_fix`
- `chapter_summary`
- `asset_compressor`
- `compressor`
- `expander`
- `persona_reader`
- `asset_generator`
- `assistant`

Reasoning tier:

- `chief_editor`
- `managing_editor`
- `chapter_planner`
- `planner`
- `auditor`
- `continuity_checker`
- `state_extractor`

## Runtime Resolution

The daily tier is the registry default. Each configured role inherits its tier model, then receives its optional role override. Explicit role overrides take precedence over inherited tier values.

The assistant keeps its dedicated override node. Without one, it inherits the daily tier.

## UI

The Agent model-routing card shows two selectors at the top: daily model and reasoning model. The routing table displays each role's inherited tier and current effective model. Existing per-role override editing remains available.

Other screens that previously displayed the main model use the daily tier as the primary text model.


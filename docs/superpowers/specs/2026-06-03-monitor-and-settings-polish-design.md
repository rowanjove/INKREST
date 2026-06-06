# Monitor And Settings Polish Design

## Goal

Improve model-library compatibility, simplify the Shanshan navigation label, let monitoring logs fill the available page height, and align the settings-page cards.

## Model Library

`DeepSeek V4 Pro` remains a built-in text-model preset. Existing model libraries are reconciled on load: missing built-in models are added, while existing entries keep user-edited parameters.

## Shanshan

The compact Shanshan navigation button uses the shorter label `监控`. Its target remains `/monitor?tab=tasks`.

## Monitor Layout

The task-monitoring tab is a viewport-aware flex column. The two log panels form a two-column grid that grows into the remaining vertical space. Each panel stretches to the same height and keeps its own internal scrollbar.

The task timeline no longer uses a fixed `max-height: 320px`, and the Agent log body no longer uses a fixed `max-height: 400px`.

## Settings Layout

Settings-page fold cards share the global card system from `App.vue`. The page applies consistent spacing and alignment for headings, supporting copy, action controls, arrows, and fold-body padding. Components should not redefine conflicting fold-card geometry locally.

## Verification

Contract tests cover model reconciliation, the short Shanshan label, flexible monitor layout, and settings-card alignment. Full backend tests and the frontend production build must pass.


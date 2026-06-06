# AI Creation Guide Redesign

## Goal

Restructure the new-project AI creation guide into a lightweight default flow with an optional deeper planning layer. The guide acts as a planning editor: it asks one focused question at a time, proposes usable directions, and lets the author accept, edit, regenerate, or skip.

## Product Structure

The default project-creation flow contains six steps:

1. Creative seed: theme, genre, and keywords.
2. Reader promise: logline, target reader, emotional experience, and core appeals.
3. Protagonist engine: identity, desire, dilemma, edge, cost, and growth direction.
4. Conflict stage: external opposition, relationship tension, world rules, and stakes.
5. Serial engine: progression path, repeatable story loop, suspense sources, and milestone goals.
6. Finalize: editable blueprint card, scale, chapter length, and optional preset composition.

After step 6, the author can create the project immediately or enter the optional deep-planning flow:

7. Character network: supporting roles and relationship tensions.
8. Growth arcs: capability, identity, emotional, and escalating-cost arcs.
9. Volume skeleton: staged volume goals, conflicts, climaxes, and ending hooks.
10. Turning points: opening event, mid-story escalation, reversal, and ending direction.

## Interaction Model

Each conversational step returns:

- one concise planning-editor response;
- zero to four candidate directions;
- the accumulated blueprint context;
- the next step number;
- whether the basic blueprint is ready;
- whether deep planning is complete;
- an editable summary card when a review surface is needed.

The finalization UI allows the author to edit the generated blueprint card, choose scale and optional preset composition, then either create immediately or continue deep planning. After deep planning, the author returns to the same finalization surface and creates the project.

## Data Model

The accumulated context stores:

- `theme`, `genre`, `keywords`;
- `reader_promise`;
- `protagonist`;
- `conflict_stage`;
- `serial_engine`;
- `summary_card`;
- `character_network`;
- `growth_arcs`;
- `volume_skeleton`;
- `turning_points`;
- scale and preset-composition fields.

Project creation writes a normalized outline to `workspace/outline.json`. The outline keeps the high-value blueprint fields so downstream outline and chapter planning can consume confirmed information rather than reconstructing it from chat text.

## Compatibility

The API remains `POST /api/novel/chat` with `step`, `user_input`, and `context`. Existing project creation remains `POST /api/projects`. The front end moves to the new 10-step contract in one change so the old 5-step card/scale mismatch is removed rather than preserved.

## Scope Boundaries

This iteration does not generate the first ten chapter plans. That remains a workspace responsibility after project creation. It also does not add persistence for an unfinished pre-creation chat session.


# Shanshan Chat Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Shanshan's initial chat readability with a welcome card, concise copy, compact suggestions, and a clearer input bar.

**Architecture:** Keep chat state unchanged. Update centralized Shanshan copy and add a first-message visual modifier in `PetBubbleView.vue`, leaving later messages on the existing bubble path.

**Tech Stack:** Vue 3, TypeScript, CSS, pytest, Vite

---

### Task 1: Add failing contract

**Files:**
- Modify: `tests/test_workspace_ui_contract.py`

- [ ] Assert concise scope copy, the capability list, the new short chips, and the `welcome` class binding.
- [ ] Run the focused test and confirm it fails.

### Task 2: Implement chat polish

**Files:**
- Modify: `web/frontend/src/constants/shanshanCopy.ts`
- Modify: `web/frontend/src/views/PetBubbleView.vue`

- [ ] Replace the initial copy and suggested questions.
- [ ] Mark the first assistant message as a welcome card.
- [ ] Tune welcome card, chips, and input-bar styles.
- [ ] Run the focused contract and confirm it passes.

### Task 3: Verify

**Files:**
- Verify only

- [ ] Run `python -m pytest -q`.
- [ ] Run `npm run build` from `web/frontend`.


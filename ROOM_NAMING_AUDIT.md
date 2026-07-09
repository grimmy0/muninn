# Room Naming & Display Clarity Audit
**Task #2: UX Review**
**Date:** 2026-03-17

## Executive Summary

The room naming system has **four critical clarity issues**:

1. **@agent label is misleading** — looks like a DM handle but is actually an inbox view
2. **Section headers misrepresent content** — "DIRECT" mixes inbox and pair rooms; "GROUP" has one room
3. **Truncation risk** — pair names with long agents (25+ chars) will truncate in 28-char sidebar
4. **Visual noise** — no distinction between different room purposes (inbox vs conversation)

---

## Critical Discovery: Message Overlap

**Integration with data-analyst findings (ROOM_ANALYSIS.md):**

Every message appears in 1-3 rooms simultaneously:
1. **Always:** #general room (all messages)
2. **If recipient matches:** @agent room (all messages TO that agent)
3. **If pair has 2+ messages:** pair room (bilateral conversation)

**UX Impact:** Users see duplicated content with misleading unread counts:
```
@alice shows: 10 unread
  ├─ 3 messages from bob
  ├─ 4 messages from carol
  ├─ 2 messages from dave
  └─ 1 from someone else

alice↔bob shows: 3 unread (SAME 3 MESSAGES)
alice↔carol shows: 4 unread (SAME 4 MESSAGES)
alice↔dave shows: 2 unread (SAME 2 MESSAGES)

Sidebar total unread = 10+3+4+2 = 19 "slots", but only 10 actual messages
```

**This fundamentally questions whether @agent rooms should exist at all** — they create visual redundancy and confusing unread counts. This is a bigger UX issue than naming alone.

---

## 1. Display Name Audit

### Current Formats
| RoomType | Format | Example | Length |
|----------|--------|---------|--------|
| GENERAL | `#general` | `#general` | 8 chars |
| AGENT | `@{name}` | `@code-reviewer` | 15 chars |
| PAIR | `{a}↔{b}` | `code-reviewer↔test-runner` | 25 chars |

### Issues

#### 1.1: @agent Label Confusion
**Problem:** The `@` prefix evokes Slack/social media DM conventions:
- Users expect `@john` to mean "direct message with John"
- Reality: `@john` is an **inbox view** — all messages **TO** john from **anyone**
- This is fundamentally different from a DM

**Evidence:** Code in `room_sidebar.py:_categorize_rooms()` shows:
- Lead's `@agent` rooms go in "TEAM LEAD" section
- Other agents' `@agent` rooms go in "DIRECT" section
- But both are inboxes! The distinction is only about lead involvement.

**User Experience Impact:**
- Clicking `@code-reviewer` shows all messages sent to code-reviewer (from any agent)
- User might expect to see only messages between them and code-reviewer
- Confusion when filtering/reading "conversations"

#### 1.2: Truncation Risk
**Sidebar width:** 28 characters (room_sidebar.py:23)

**Available space for labels (estimated):**
- Tree indentation: ~2-3 chars
- Available: ~24-25 chars per label

**Names that will truncate:**
```
"code-reviewer↔test-runner"        = 25 chars (BORDERLINE, truncates with indent)
"code-reviewer↔test-runner-agent"  = 32 chars (DEFINITELY TRUNCATES)
"data-scientist↔model-validator"   = 28 chars (TRUNCATES)
```

**With unread badges** `" (12)"` (4 chars):
```
"code-reviewer↔test-runner (5)"    = 29 chars (TRUNCATES)
```

**Impact:**
- Pair names with 2+ multi-word agent names will truncate
- User can't read full pair name without hovering
- Reduces at-a-glance room recognition

---

## 2. Section Header Clarity

### Current Categorization (in `_categorize_rooms`)
```python
"TEAM LEAD" → rooms involving lead_agent_id
"GROUP"     → RoomType.GENERAL (#general)
"DIRECT"    → everything else
```

### Analysis

#### "TEAM LEAD" ✓ Reasonable
- Contains `@lead_agent` room (inbox for the lead)
- Contains `lead_agent↔other_agent` pair rooms
- Communicates: "rooms involving the team lead"

#### "GROUP" ⚠ Misleading
- **Contains:** Only `#general`
- **Problem:** Single-item section feels verbose
- **Terminology:** "GROUP" suggests multiple items, but there's only one room
- **Better term:** "[Broadcast]" or "[All]" or "[General]"

#### "DIRECT" ❌ Highly Misleading
- **Contains:**
  - `@agent` rooms (inboxes) — NOT direct conversations
  - `pair_agent1↔pair_agent2` rooms (actual conversations)
- **Problem:** Mixes two fundamentally different room purposes
  - Inbox rooms: "messages TO this agent from anyone"
  - Pair rooms: "messages between these two agents"
- **Better structure:** Split into two sections
  - "[Inboxes]" → `@agent` rooms
  - "[Conversations]" → `pair` rooms

---

## 3. Truncation Risk Analysis

### Space Calculation
With sidebar width=28, tree indentation, and section headers:

| Scenario | Available Chars | Example | Status |
|----------|-----------------|---------|--------|
| Short pair | ~23 chars | `alice↔bob` (9) | ✓ OK |
| Medium pair | ~23 chars | `code-reviewer↔qa-tester` (23) | ✓ OK (tight) |
| Long pair | ~23 chars | `code-reviewer↔test-runner` (25) | ❌ TRUNCATES |
| Long + badge | ~19 chars | `"...↔test-runner (5)"` | ❌ TRUNCATES |

### At-Risk Names
Teams with multi-word agent names (common for functional roles):
- `data-scientist↔data-validator` (28 chars)
- `backend-engineer↔frontend-engineer` (34 chars)
- `security-team↔compliance-team` (29 chars)

**Worst case (5-agent team with long names):**
- 5 @agents + 10 pair rooms = 15 rooms total
- ~30-40% of pair rooms truncate beyond first few teams

---

## 4. Visual Noise & Scalability

### Room Count Growth
For N agents with active conversations:
- **#general:** 1 room (always)
- **@agents:** 1-N rooms (one per agent with messages TO them)
- **Pairs:** up to N*(N-1)/2 rooms (if each pair has 2+ messages)

**Examples:**
| Team Size | Potential Rooms | Density |
|-----------|-----------------|---------|
| 3 agents | 1 + 3 + 3 = 7 | Low |
| 5 agents | 1 + 5 + 10 = 16 | Medium-High |
| 10 agents | 1 + 10 + 45 = 56 | Very High |

### User Impact
- With 16 rooms, sidebar becomes long to scroll
- No visual hierarchy distinguishing inbox from conversation rooms
- Users can't quickly identify "which rooms need attention" vs "which are just inboxes"

---

## 5. Unread Badge Format

**Current:** `name (3)` appended to label

**Assessment:** Clear and follows common patterns ✓

**However:** Contributes to truncation when combined with long names

---

## 6. Proposed Improvements

### CRITICAL: Architectural Decision First

**Before naming changes, decide @agent room lifecycle:**

**Option X1: Remove @agent rooms entirely**
- **Pro:** Eliminates message overlap, simpler UI, cleaner sidebar
- **Con:** Loses "inbox" view for broadcast scenarios (lead receiving from many agents)
- **Best for:** Teams with primarily bilateral conversations
- **Risk:** High-volume leads might miss cross-team overview

**Option X2: Keep @agent but fix display overlap**
- **Pro:** Retain inbox functionality for broadcasts
- **Con:** Requires complex UI logic to prevent double-counting unread messages
- **Implementation:** Don't show pair room unread badges if @agent room visible, or visual indication of overlap
- **Best for:** Teams with mixed broadcast + bilateral patterns

**Option X3: Keep both but restructure categorization**
- **Pro:** Maximum functionality, users can choose
- **Con:** Sidebar confusion continues, naming alone won't fix it
- **Implementation:** Split into [Broadcasts], [Inboxes], [Conversations] sections
- **Best for:** Power users who understand the overlap

**RECOMMENDATION:** Choose X1 or X2. X3 doesn't solve the core problem.

---

### Option A: Rename @agent Inboxes to Something Clearer

**Current:** `@code-reviewer`
**Proposed:** `↙ code-reviewer` or `⬅ code-reviewer`

- **↙** = inbox symbol (leftward-pointing arrow suggests incoming)
- **⬅** = simpler leftward arrow
- Visually distinct from `#` (broadcast) and `↔` (pair)
- Shorter than `@`, leaving more space

**Or text-based:**
- `i: code-reviewer` (i = inbox)
- `in: code-reviewer`

### Option B: Restructure Section Headers

**Current:**
```
[TEAM LEAD]
  @lead-agent
  lead-agent↔other-agent

[GROUP]
  #general

[DIRECT]
  @other-agent
  @another-agent
  agent1↔agent2
  agent3↔agent4
```

**Proposed (Split DIRECT):**
```
[TEAM LEAD]
  ↙ lead-agent
  lead-agent↔other-agent

[General]
  #general

[Inboxes]
  ↙ code-reviewer
  ↙ data-scientist
  ↙ qa-tester

[Conversations]
  code-reviewer↔qa-tester
  data-scientist↔qa-tester
```

**Benefits:**
- Visual grouping by purpose
- Section names accurately describe content
- Users understand at-a-glance what each section contains

### Option C: Abbreviate Long Pair Names

**For pairs exceeding 20 chars:**
```
code-reviewer↔test-runner      = "cr↔tr" (abbreviated)
code-reviewer↔test-runner      = "cr↔test-runner" (first abbreviated)
```

**Tradeoff:** Users can't read full names in sidebar, need hover tooltip

---

## 7. Recommended Action Plan

### Phase 1: Clarify @agent semantics (High Priority)
1. Rename `@agent` to `↙ agent` or similar
2. Update `display_name` property in `room.py`
3. This immediately fixes the misleading label

### Phase 2: Restructure section headers (High Priority)
1. Split "DIRECT" into "[Inboxes]" and "[Conversations]"
2. Rename "GROUP" to "[General]" or "[Broadcast]"
3. Update `_categorize_rooms()` in `room_sidebar.py`

### Phase 3: Truncation mitigation (Medium Priority)
1. Add tooltip on hover showing full room name
2. Consider abbreviation strategy for very long names
3. Monitor sidebar space in wider/narrower windows

### Phase 4: Testing (After implementation)
1. Visual regression test with team simulation (5+ agents)
2. Verify truncation at 28-char width
3. Confirm unread badges still fit
4. Check accessibility of new symbols

---

## Files to Modify

1. **`src/muninn/models/room.py`**
   - Update `display_name` property to use new format

2. **`src/muninn/widgets/room_sidebar.py`**
   - Update `_categorize_rooms()` to split DIRECT
   - Add section headers for inbox vs pair distinction

3. **`tests/test_*`**
   - Add tests for new display_name formats
   - Add tests for section categorization

---

## Questions for Team Lead

1. **Symbol preference:** Prefer `↙`, `⬅`, `i:`, or `in:` for inbox notation?
2. **Abbreviation:** Should very long pair names be abbreviated or full-width truncated?
3. **Hover tooltips:** Resources for adding full-name tooltips in Textual?
4. **Pair room naming:** Should "pair" name in code be displayed as agent 1 or sorted alphabetically?


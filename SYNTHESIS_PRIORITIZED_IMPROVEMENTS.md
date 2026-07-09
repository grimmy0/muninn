# Room Discovery System: Synthesized Findings & Prioritized Improvements

**Synthesis Date:** 2026-03-17
**Source Documents:** ROOM_ANALYSIS.md, ROOM_NAMING_AUDIT.md, ANALYSIS_STRUCTURED_MESSAGES.md
**Team:** data-analyst + ux-reviewer + test-engineer

---

## Executive Summary

The room discovery system creates **significant message overlap, naming confusion, and protocol noise**. Three major issues compound each other:

1. **Structural Overlap:** Every message appears in 1-3 rooms simultaneously (#general, @agent, pair)
2. **Naming Confusion:** @agent rooms look like DM handles but are actually inbox views
3. **Protocol Noise:** 100% protocol-only rooms waste sidebar space with zero conversational value

**Impact:** Users cannot distinguish between inbox-style rooms and conversation rooms, and must navigate through redundant messaging patterns and hidden protocol rooms.

---

## Problem Synthesis

### Problem #1: Message Overlap (Data-Analyst Finding)

**The Issue:**
Every message is indexed in three data structures simultaneously, creating rooms that contain overlapping messages:

```
Message A→B appears in:
  ✓ #general (always)
  ✓ @B inbox (all messages TO B)
  ✓ A↔B pair room (if 2+ messages exist)
```

**User Impact:**
- @alice shows: [messages TO alice from bob, carol, dave, ...]
- alice↔bob shows: [same messages from bob that are in @alice]
- User clicks @alice (10 unread), then alice↔bob (3 unread), seeing same 3 messages twice
- Confusing: Is this new content or something I already saw?

**Root Cause:**
- Indexing strategy creates rooms for both inbox (recipient-based) and pair (pair-based) views
- No distinction in UI between "these messages appear multiple places" vs "these are new messages"

---

### Problem #2: Misleading Naming & UI (UX-Reviewer Finding)

**The Issues:**

#### Issue 2a: @agent naming is misleading
- **Current:** Looks like a social media DM handle (@alice) but is actually "inbox of all messages TO alice"
- **Users expect:** DM with just alice
- **They get:** All messages from anyone TO alice
- **Result:** Confusion about what @alice contains

#### Issue 2b: Section headers don't match content
| Section | Actual Content | User Expectation |
|---------|---|---|
| "TEAM LEAD" | @lead + all pair rooms with lead | Rooms about the lead |
| "GROUP" | Only #general | Team-wide conversation |
| "DIRECT" | @other agents + all other pairs | Direct 1:1 conversations |

- "DIRECT" is wildly inaccurate: mixes inbox views with pair conversations
- "GROUP" is a single room, suggesting multiple rooms
- Users cannot predict where to find a specific room

#### Issue 2c: No visual distinction
- @alice and alice↔bob look identical in sidebar
- No icon, color, or prefix to indicate "this is an inbox" vs "this is a pair conversation"
- Users must read the name carefully to understand the difference

#### Issue 2d: Truncation risk
- Available width: ~24-25 characters (28-char sidebar minus tree indentation)
- Unread badge adds 4 chars: " (12)"
- Pair room names: "code-reviewer↔test-runner" = 25 characters
- Long names get truncated: "code-reviewer↔test-run..." (unreadable)

---

### Problem #3: Protocol Noise (Test-Engineer Finding)

**The Issue:**
Pure protocol-only rooms are created that serve zero user value:

#### Pattern 1: Task Assignment → Response Loops
```
team-lead sends task_assignment to analyst
analyst responds with permission_request
→ Creates analyst↔team-lead pair room
→ 100% of messages are structured/protocol
→ No conversational value
→ Duplicates Tasks tab
```

#### Pattern 2: Broadcast Duplication
```
team-lead broadcasts task to [analyst, researcher, auditor]
→ Creates @analyst room, @researcher room, @auditor room
→ Same broadcast appears in all three
→ Also creates 3 pair rooms: lead↔analyst, lead↔researcher, lead↔auditor
→ Same message appears 7 times in sidebar (1 broadcast + 3 @agent + 3 pair)
```

#### Pattern 3: Idle-Only Rooms
```
Only messages in certain rooms are idle_notifications
→ Room contains zero conversational content
→ Clutters sidebar with status updates
```

#### Pattern 4: Task-Only Pair Rooms
```
Agents A and B never converse, only exchange task assignments
→ Creates A↔B pair room
→ 100% of messages are task_assignments
→ Duplicates Tasks tab (which already shows all tasks)
```

**Root Cause:**
- `discover_rooms()` creates rooms based purely on message count/pair existence
- No filtering for message type or conversational value
- Protocol messages treated same as user messages

---

## Synthesized Root Causes

### Root Cause 1: Data Model Doesn't Distinguish Message Type
- All messages mixed: conversational, protocol, system
- No content-based filtering when creating/displaying rooms

### Root Cause 2: Multiple Indexing Creates Necessary Overlap
- Inbox view (by recipient) is useful for broadcast scenarios
- Pair view (by pair) is useful for bilateral conversation
- Both needed, but creates overlapping message sets

### Root Cause 3: Naming Based on Technical Implementation, Not User Mental Model
- @agent comes from code structure (_by_recipient)
- Pair naming comes from pair_key data structure
- Names don't communicate purpose to users

### Root Cause 4: No Categorization by Purpose
- All rooms treated equal in sidebar
- No grouping by "inbox" vs "conversation" vs "protocol"

---

## Prioritized Improvement List

### TIER 1: High Impact, Low Effort (Do First)

#### 1.1 Filter Protocol-Only Rooms from Sidebar
**Impact:** Eliminates the most confusing noise
**Effort:** Medium (requires code change but clear scope)
**Action:** Modify `discover_rooms()` or create `get_sidebar_rooms()` that filters out:
  - Rooms where 100% of messages are structured/protocol type
  - Idle-notification-only rooms
  - Task-assignment-only rooms

**Code Location:** `message_store.py::discover_rooms()` or create new method
**Affected UI:** Sidebar only (messages still accessible via Tasks tab or search)
**Expected Impact:**
  - Remove 10-40% of rooms in typical team (all pure-protocol pairs)
  - Reduce unread count cognitive load

**Test Cases:**
  - Pure-protocol pair room should not appear
  - Mixed (protocol + conversation) rooms should appear
  - Tasks tab still shows all task messages

---

#### 1.2 Rename @agent Rooms to Clearer Symbol + Section Split
**Impact:** Fixes the #1 source of user confusion
**Effort:** Low (UI/display change)
**Action:**
  - Rename @agent rooms to use prefix that says "inbox"
  - Split "DIRECT" section into ["Inboxes"] and ["Conversations"]
  - Add brief tooltips on hover

**Code Location:** `room.py::display_name`, `room_sidebar.py::_categorize_rooms()`
**Changes:**
```python
# Old: @alice
# New: ↙ alice (or other inbox symbol)
# Or:  [alice inbox] or [alice ⬅️]

# Old sidebar:
# TEAM LEAD
#   @lead
#   lead↔bob
#   lead↔carol
#
# DIRECT
#   @alice
#   @bob
#   alice↔bob
#   carol↔dave

# New sidebar:
# TEAM LEAD
#   ↙ lead
#   lead ↔ bob
#   lead ↔ carol
#
# INBOXES (messages TO you)
#   ↙ alice
#   ↙ bob
#
# CONVERSATIONS (bilateral)
#   alice ↔ bob
#   carol ↔ dave
```

**Expected Impact:**
  - Users immediately understand the difference
  - No more confusion about what @alice contains
  - Clear visual structure

**Test Cases:**
  - @agent displayed with new symbol
  - Sidebar sections split correctly
  - Lead's rooms still in TEAM LEAD section

---

#### 1.3 Add Visual Distinction Between Room Types
**Impact:** Reinforces naming/section split
**Effort:** Low (CSS + icon change)
**Action:**
  - Add icon prefix: ↙ for inboxes, ↔ for pairs, # for general
  - Add light background color differentiation
  - Style lead rooms differently (bold, accent color)

**Code Location:** `room_sidebar.py`, `room.py::display_name`, CSS in room_sidebar.py
**Expected Impact:**
  - Scannability improves
  - Users don't have to read carefully to understand room type

---

#### 1.4 Handle Long Pair Room Names (Truncation Fix)
**Impact:** Prevents unreadable truncated names
**Effort:** Low (CSS/JS change)
**Action:**
  - Implement ellipsis handling with tooltip
  - Or abbreviate agent names: "code-reviewer↔test-runner" → "cr↔tr"
  - Or truncate at agent boundary: "code-reviewer↔test..." → "code↔test..."

**Code Location:** `room.py::display_name` or CSS in room_sidebar.py
**Expected Impact:**
  - Long pair names remain readable
  - Users can still identify the conversation

---

### TIER 2: High Impact, Medium Effort (Plan Next)

#### 2.1 Redesign #general Room Placement
**Impact:** Reduces cognitive load for common case
**Effort:** Medium (requires product decision)
**Action:**
  - Move #general to separate "System" section at bottom
  - Or add toggle to hide #general unless user explicitly searches for it
  - Or create dedicated "Audit" view separate from daily sidebar

**Rationale:**
  - #general is useful for compliance/audit, not daily workflow
  - Most users ignore it after initial check
  - Wastes sidebar space

**Expected Impact:**
  - Sidebar more focused on relevant conversations
  - Reduces choice overload

---

#### 2.2 Consolidate Lead-Related Rooms (Categorization Revisit)
**Impact:** Clarifies which rooms a lead should prioritize
**Effort:** Medium (requires rethinking categorization)
**Issue:** Currently all lead-related rooms in "TEAM LEAD" section, including both inboxes and pairs
**Action:**
  - Keep pairs in TEAM LEAD (important conversations)
  - Move lead's inbox (↙ lead) to "INBOXES" section instead
  - Rationale: Lead's inbox is "messages TO me" (same as everyone's inbox), not a special "TEAM LEAD" concern

**Expected Impact:**
  - "TEAM LEAD" section becomes "Bilateral conversations with lead"
  - Clearer organizational structure

---

### TIER 3: Architectural Decision Required

#### 3.1 Decide: Prioritize Pair Rooms vs Keep @agent Rooms
**Impact:** Determines long-term room discovery strategy
**Effort:** High (architectural change)
**Decision Points:**
  - **Option A: Prioritize Pair Rooms** - Remove @agent rooms, rely on pair conversations only
    - Pro: No overlap, simpler mental model
    - Con: Loose "inbox" view for managers receiving from many agents
  - **Option B: Keep Both, Improve Context** - Keep @agent + pair, but make overlap clear
    - Pro: Preserves broadcast/inbox functionality
    - Con: Requires more complex UI to explain overlap
  - **Option C: Context-Dependent** - Only show @agent for high-volume receivers (5+ senders)
    - Pro: Flexible, adapts to actual usage
    - Con: Complex logic, inconsistent UX

**Recommendation:** Based on analysis, **Option B (Keep Both, Improve Context)** is best because:
  - Some users genuinely benefit from inbox view (managers, leads)
  - Most users benefit from pair-room focus (bilateral conversations)
  - Tier 1-2 improvements make overlap clear and manageable
  - Avoids losing functionality for edge cases

---

## Implementation Roadmap

### Phase 1: Low-Effort Wins (1-2 days)
1. Filter protocol-only rooms (1.1)
2. Rename @agent rooms + split sections (1.2)
3. Add visual distinction (1.3)
4. Truncation fix (1.4)

**Blockers:** None
**Testing:** New tests for display_name format, sidebar categorization
**Deployment:** Can ship incrementally

### Phase 2: Refinement (1 week)
5. Redesign #general placement (2.1)
6. Revisit categorization (2.2)

**Blockers:** Product decision on #general importance
**Testing:** User feedback on sidebar clarity

### Phase 3: Architectural (2+ weeks)
7. Decide on pair vs inbox priority (3.1)
8. Implement chosen strategy

**Blockers:** Stakeholder alignment on room discovery philosophy
**Impact:** Potential redesign of discover_rooms() method

---

## Test Coverage Required

### Phase 1 Tests
- Protocol-only rooms are filtered from discover_rooms()
- Mixed protocol+conversation rooms still appear
- @agent display_name shows new format
- Sidebar sections split correctly
- Long pair names don't cause layout issues

### Integration Tests
- Total room count: 1 (#general) + agents_with_messages + pairs_with_2+_msgs - pure_protocol_rooms
- Unread counts are accurate per room
- Messages appear in correct rooms based on type

### User Testing
- Users can distinguish inbox from pair rooms
- Users understand why same message appears in multiple places
- Users find relevant rooms quickly (scan sidebar)

---

## Cross-Team Coordination

**Data-Analyst → UX-Reviewer:**
- Protocol filtering will reduce rooms by 10-40%, affecting sidebar load
- Naming redesign should account for space constraints (24-25 char width)

**Data-Analyst → Test-Engineer:**
- New filtering logic needs comprehensive testing
- Edge cases: agent with only protocol messages, broadcast messages, idle notifications

**UX-Reviewer → Test-Engineer:**
- Truncation handling needs visual testing
- Section splitting needs integration tests

---

## Metrics to Track

After implementation:
1. **Sidebar clutter:** Average number of rooms per user (should decrease)
2. **Click confusion:** Unread messages per room (should decrease overlap visibility)
3. **User satisfaction:** Sidebar organization clarity (survey)
4. **Navigation efficiency:** Time to find specific conversation (should improve)

---

## Open Questions

1. **Priority of #general room:** Is audit trail more important than daily workflow clarity?
2. **Lead room strategy:** Should leads see @lead and lead↔X separately, or consolidated?
3. **Broadcast handling:** Should broadcasts create multiple @agent rooms, or single broadcast room?
4. **Threshold refinement:** Is 2-message pair threshold optimal, or should it be dynamic?

---

## Summary Table

| Issue | Root Cause | Tier 1 Fix | Impact |
|-------|-----------|-----------|--------|
| Overlap confusion | Multiple indexing strategies | Improve naming/sections | High |
| Protocol noise | No content filtering | Filter pure-protocol | High |
| @agent misleading | Poor naming | Rename to inbox symbol | High |
| Truncation | Long names | Add ellipsis/abbreviate | Medium |
| #general overwhelming | Always included | Move to separate section | Medium |
| Categorization ambiguity | No distinction by type | Split DIRECT section | High |

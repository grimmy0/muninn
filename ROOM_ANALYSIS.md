# Room Discovery Logic Analysis: Redundancy & Overlap

**Analysis Date:** 2026-03-17
**Analyzer:** data-analyst
**Status:** Initial findings

---

## 1. Room Creation Inventory

The `discover_rooms()` method creates three types of rooms:

### Room Type A: #general (Single Room)
- **Created:** Always (if any messages exist)
- **Contains:** ALL messages in the system
- **Message filter:** No filter - includes everything
- **Agents field:** Tuple of all known agents
- **Code location:** message_store.py:111-118

### Room Type B: @agent (One per agent with messages)
- **Created:** For each agent in `known_agents` that has received at least 1 message
- **Contains:** All messages where `recipient == agent`
- **Message filter:** Indexed by recipient only
- **Agents field:** Single-element tuple with agent name
- **Code location:** message_store.py:121-131
- **Example:** @alice contains: [bob→alice, carol→alice, dave→alice, ...]

### Room Type C: PAIR (One per agent pair with 2+ messages)
- **Created:** For each unique agent pair in `_by_pair` with ≥2 messages
- **Contains:** Bidirectional messages between exactly two agents
- **Message filter:** Both directions sorted alphabetically
- **Agents field:** Two-element tuple (sorted: [a, b] if a ≤ b)
- **Code location:** message_store.py:133-149
- **Threshold:** Minimum 2 messages required for pair room to exist
- **Sorting:** Displayed in sidebar by message count (descending)
- **Example:** alice↔bob contains: [alice→bob message 1, bob→alice message 1, alice→bob message 2, ...]

---

## 2. Message Storage & Indexing

All messages are indexed three ways simultaneously:

```python
# Line 70, 66, 68 in load_inbox_file():
self._all_messages.append(msg)              # Global list
self._by_recipient[recipient].append(msg)   # Indexed by recipient
self._by_pair[pair_key].append(msg)         # Indexed by pair
```

**Every message gets stored in all three indices.**

---

## 3. Overlap Matrix: Example Scenario

### Scenario Setup
Team with 3 agents (A, B, C) sending messages:
- A → B (message 1)
- B → A (message 2)
- A → C (message 3)
- B → C (message 4)

### Room Contents & Overlap

| Message | #general | @A room | @B room | @C room | A↔B pair | A↔C pair | B↔C pair |
|---------|----------|---------|---------|---------|----------|----------|----------|
| A→B     | ✓        | ✗       | ✓       | ✗       | ✓        | ✗        | ✗        |
| B→A     | ✓        | ✓       | ✗       | ✗       | ✓        | ✗        | ✗        |
| A→C     | ✓        | ✗       | ✗       | ✓       | ✗        | ✗        | ✗        |
| B→C     | ✓        | ✗       | ✗       | ✗       | ✗        | ✗        | ✗        |

**Pair rooms created:** Only A↔B (has 2 messages). A↔C and B↔C don't exist (only 1 message each).

### Appearance Count per Message
- **A→B**: 3 rooms (#general, @B, A↔B)
- **B→A**: 3 rooms (#general, @A, A↔B)
- **A→C**: 2 rooms (#general, @C) ← No A↔C pair room
- **B→C**: 2 rooms (#general, @C) ← No B↔C pair room

**Key insight:** Messages appear in 2-3 different rooms depending on whether a pair room threshold is met.

---

## 4. @agent Rooms vs PAIR Rooms: Functional Comparison

### @agent Room (Inbox View)
- **Purpose:** Show all messages received by one agent, from any sender
- **Use case:** "Show me everything sent to me"
- **Example @alice:**
  - Contains: [bob→alice, carol→alice, dave→alice, eve→alice, ...]
  - Shows messages from 5+ different senders
  - Like an "inbox" in email

**Strengths:**
- Consolidates all incoming messages to one agent
- Useful when agent receives from many different senders
- Single view of "what I've received"

**Weaknesses:**
- No sender context - messages from different people mixed together
- If most communication is bilateral, creates redundancy with pair rooms
- Can be overwhelming if agent receives from 20+ senders

### PAIR Room (Conversation View)
- **Purpose:** Show complete bilateral conversation between two agents
- **Use case:** "Show me the conversation between Alice and Bob"
- **Example alice↔bob:**
  - Contains: [alice→bob msg1, bob→alice msg1, alice→bob msg2, bob→alice msg2, ...]
  - Messages only from this specific pair
  - Chronologically ordered

**Strengths:**
- Shows complete conversation thread
- Clear bilateral context
- Isolated from other conversations
- Better for focused discussion

**Weaknesses:**
- Fragmented for agents with many conversations
- Manager with 10 direct reports needs 10 pair rooms to see all their messages
- More rooms to navigate

### When is @agent useful that PAIR isn't?

**Answer:** When the agent receives messages from many different senders.

**Example A (Broadcast Scenario):**
- 15 team members all message the team lead at different times
- @lead shows: 15+ messages in one place (inbox view)
- Would require: 15 pair rooms (lead↔member1, lead↔member2, ..., lead↔member15)
- **Verdict:** @lead is clearly more useful here

**Example B (Peer Conversation):**
- Alice mostly talks with Bob (5 messages)
- Alice also gets 1 message each from Carol and Dave
- @alice shows: [bob→alice×5, carol→alice×1, dave→alice×1]
- alice↔bob shows: [bob→alice×5]
- **Verdict:** Pair room is more useful for focused conversation; @alice adds noise

### When is PAIR useful that @agent isn't?

**Answer:** When you want to see bidirectional conversation between two specific people.

- PAIR shows: [A→B msg1, B→A msg1, A→B msg2, B→A msg2, ...]
- @A shows: [B→A msg1, C→A msg1, B→A msg2, ...]
- @B shows: [A→B msg1, C→B msg1, A→B msg2, ...]
- **Verdict:** Only PAIR room shows the full conversation in proper sequence

---

## 5. #general Room Analysis

### What it Contains
- Every single message ever loaded
- No filtering - includes all senders, recipients, conversations
- Always exists and appears first in sidebar

### Is it Useful?

**Use cases where #general is valuable:**
1. **Audit/compliance:** Need comprehensive record of all communication
2. **Full-text search:** Finding a message when you don't know who sent it
3. **Initial onboarding:** Understanding all team activity at a glance
4. **Debugging:** Reconstructing message flow across system

**Use cases where #general is problematic:**
1. **Workflow:** 1000+ messages is overwhelming
2. **Navigation:** Hard to find relevant conversation
3. **Focus:** Mixing all conversations together creates noise
4. **UX:** Users probably never click into #general after initial setup

**Recommendation:** Keep #general but consider de-emphasizing in UI (move to bottom, different styling, or optional search interface)

---

## 6. Pair Room Threshold Analysis

### Current Threshold: 2+ messages

```python
# message_store.py:136
if len(msgs) >= 2:
    pair_counts.append((pair_key, len(msgs)))
```

### Is 2 the right number?

**Arguments for 2:**
- ✓ Ensures bidirectional conversation (A→B and B→A)
- ✓ Eliminates single-message "noise" rooms
- ✓ Matches typical conversation pattern (at least one exchange)
- ✓ Reasonable default

**Arguments for higher (e.g., 3+):**
- Might reduce clutter in very high-volume teams
- But 2 messages is genuinely a conversation (one exchange)

**Arguments for lower (e.g., 1+):**
- No benefits - single message doesn't warrant a "room"

**Verdict:** 2 is correct. Don't change.

---

## 7. Categorization in Sidebar: Overlap Issue

### Current Logic (_categorize_rooms in room_sidebar.py:62-75)

```
#general → "GROUP" section
@agent room → "TEAM LEAD" (if agent == lead_agent_id)
@agent room → "DIRECT" (otherwise)
pair room → "TEAM LEAD" (if lead_agent_id in pair)
pair room → "DIRECT" (otherwise)
```

### The Categorization Problem

When lead_agent_id is set (e.g., "alice"), the sidebar shows:

```
TEAM LEAD:
  @alice (10 unread)
  alice↔bob (3 unread)
  alice↔carol (4 unread)
  alice↔dave (2 unread)

DIRECT:
  bob↔carol
  carol↔dave
  ...

GROUP:
  #general
```

### The Issue

**Same messages appear in multiple rooms:**
- The 3 messages in alice↔bob are a SUBSET of the 10 messages in @alice
- The 4 messages in alice↔carol are a SUBSET of the 10 messages in @alice
- User sees unread counts for all: total looks like 10+3+4+2=19, but it's actually 10

**When user clicks:**
1. Clicks @alice → sees all 10 messages
2. Clicks alice↔bob → sees same 3 messages (redundant)
3. User is confused: "Why is this conversation showing again?"

### Why This Happens

The sidebar code doesn't account for message overlap when displaying unread counts. It shows the unread count for each room independently, which makes the total appear larger than it is.

**Example with actual numbers:**
- alice receives 10 messages total
- 3 from bob (shown in @alice AND alice↔bob)
- 4 from carol (shown in @alice AND alice↔carol)
- 2 from dave (shown in @alice AND alice↔dave)
- 1 from someone else

Sidebar shows: @alice (10) + alice↔bob (3) + alice↔carol (4) + alice↔dave (2) = 19 unread "slots", but only 10 actual messages.

### Options to Fix

1. **Remove @agent rooms entirely** - Use only pair rooms
   - Pro: No overlap, simpler
   - Con: Loses "inbox" view for broadcast scenarios

2. **Remove @agent rooms for leads** - Only show pair rooms for lead
   - Pro: Cleaner sidebar for lead view
   - Con: Lead can't see inbox-style view of all incoming messages

3. **Keep both but adjust sidebar display** - Hide overlapping messages
   - Pro: Keep functionality
   - Con: Complex logic to prevent overlap display

---

## 8. Current Overlaps Summary

### Direct Message Overlap
Every message exists in 1-3 rooms:
1. **Always:** #general room
2. **If recipient exists:** @recipient room
3. **If pair has 2+ messages:** pair room

### Room Redundancy Levels

**Low redundancy:** Pair rooms (contain unique bilateral conversations)
**Medium redundancy:** @agent rooms (contain subset of messages, consolidate from multiple senders)
**High redundancy:** #general (contains everything)

### Total Rooms Created for N Agents with M Messages

- Always: 1 (#general)
- Maximum @agent rooms: N (one per agent)
- Maximum pair rooms: N×(N-1)/2 (one per possible pair, minus threshold)
- Actual count: 1 + (agents with messages) + (pairs with 2+ messages)

---

## Recommendations Summary

| Room Type | Keep? | Reasoning |
|-----------|-------|-----------|
| #general  | YES*  | Needed for audit/search, but de-emphasize in daily UI |
| @agent    | MAYBE | Useful for broadcast scenarios, redundant for bilateral-only teams |
| pair      | YES   | Core conversation view, least redundancy |

**Key Decision: Should @agent rooms be the primary view, or pair rooms?**
- If team is mostly bilateral conversations: **Prioritize pair rooms**
- If team has broadcast patterns (lead messaging many): **Keep @agent rooms for leads**
- Current approach: Keep both, creating overlap

---

## Next Steps for Other Teams

**For ux-reviewer:**
- Decide if sidebar redundancy is acceptable (seeing same messages in multiple rooms)
- Consider UI changes to make overlap clearer to users
- Evaluate if #general should be demoted in sidebar

**For test-engineer:**
- Test overlap behavior: verify same message appears in correct rooms
- Test threshold: verify A↔B with exactly 2 messages creates room, 1 message doesn't
- Test categorization: verify lead rooms are separated correctly

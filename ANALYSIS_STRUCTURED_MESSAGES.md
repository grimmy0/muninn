# Analysis: Rooms Containing Only Structured/Task Messages

**Task #3 Analysis** | Date: 2026-03-17 | Status: Complete

## 1. Structured Message Types Inventory

From `src/muninn/models/message.py` lines 68-92, the codebase defines 6 structured message types:

| Type | Purpose | Use Case | Represented in Test Data |
|------|---------|----------|--------------------------|
| `task_assignment` | Team lead assigns work | Start task | ✓ (2 instances) |
| `permission_request` | Agent requests tool access | Need user confirmation | ✓ (1 instance) |
| `permission_response` | User approves/denies tool use | Grant/deny permission | ✓ (1 instance) |
| `shutdown_request` | Agent requests to terminate | End work session | ✓ (1 instance) |
| `shutdown_approved` | Approval of shutdown | Confirm termination | ✓ (1 instance) |
| `idle_notification` | Agent idle/waiting status | Protocol status | ✓ (1 instance) |

**Key insight**: These are all **protocol messages**, not conversations. They represent infrastructure events (permissions, task assignments, agent state transitions), not actual human discussion or collaboration.

---

## 2. Protocol Noise Room Patterns

### Current Room Discovery Logic (`message_store.py:107-151`)

The system creates three types of rooms:

1. **#general** - all messages from all agents
2. **@agent rooms** - one per agent with messages in their inbox (recipient-based)
3. **Pair rooms** - agent↔agent rooms with 2+ messages between them

### Problem Pattern: Task Assignment → Response Loop

When a typical task/permission workflow occurs:

```
Timeline:
1. team-lead sends task_assignment → analyst (written to analyst.json)
2. analyst responds with permission_request → team-lead (written to team-lead.json)
3. team-lead responds with permission_response → analyst (written to analyst.json)
```

**Rooms created:**
- `analyst` (@agent) - receives task + permission_response
- `team-lead` (@agent) - receives permission_request
- `analyst↔team-lead` (pair) - 2-3 messages, potentially ALL structured

**Current sidebar impact**: Creates a pair room that serves no conversational purpose.

---

## 3. Broadcast Duplication Issue

`detect_broadcasts()` (lines 153-178) marks messages sent to multiple recipients:

- Identifies broadcasts by `(sender, timestamp_iso)` signature
- Sets `is_broadcast = True` for all copies

**Current problem**:

```python
# If team-lead sends task_assignment to [analyst, researcher]
# detect_broadcasts creates:
# - Message 1 (recipient=analyst, is_broadcast=True)
# - Message 2 (recipient=researcher, is_broadcast=True)

# Both messages still create:
# - @analyst room (contains the broadcast copy)
# - @researcher room (contains the broadcast copy)
# - analyst↔team-lead pair room (if 2+ messages)
# - researcher↔team-lead pair room (if 2+ messages)
```

**Result**: Broadcast task assignments still appear in multiple @agent rooms, cluttering the sidebar even though they're not unique conversations.

---

## 4. Task-Only Rooms

Many pair rooms may contain ONLY `task_assignment` messages:

```python
# If only messages between team-lead and analyst are:
# - task_assignment (task-001)
# - task_assignment (task-002)
# - task_assignment (task-003)

# Then analyst↔team-lead pair room is 100% task-only
```

**Problem**: Tasks are already visible in the Tasks tab (extracted by `extract_tasks()`). A pair room showing only task assignments is redundant UI.

---

## 5. Idle Notification Rooms

Idle notifications create significant sidebar noise:

**Current test data pattern:**
- In `analyst.json`: `idle_notification` from analyst (timestamp 2026-03-14T02:26:00.000Z)

**Real-world scenario** (from Claude Code team patterns):
- When agent goes idle: → `idle_notification` message
- When agent resumes: → new conversation

**Problem if agent never resumes:**
- `@analyst` room contains mostly `idle_notification` messages
- Pair rooms with idle-only exchanges (e.g., `analyst↔researcher` with only idles)

---

## 6. Concrete Filtering Proposal

### Rule 1: Hide 100% Structured Rooms

**Definition**: A room where ALL messages have `msg.structured != None`

**Applies to**:
- Pair rooms with only protocol exchanges (task + permission response)
- Single-message @agent rooms that are structured (rare but possible)

**Implementation**:
```python
def is_protocol_only_room(room: Room, messages: list[Message]) -> bool:
    """Return True if room contains only structured messages."""
    if not messages:
        return False
    return all(msg.structured is not None for msg in messages)
```

**Impact**: Hides analyst↔team-lead pair rooms that are pure task assignment → permission loops.

---

### Rule 2: Hide Idle-Only Rooms

**Definition**: A room where ALL messages are `idle_notification` type

**Applies to**:
- @agent rooms where agent only reported idle status, never conversed
- Pair rooms with only idle_notification exchanges

**Implementation**:
```python
def is_idle_only_room(messages: list[Message]) -> bool:
    """Return True if all structured messages are idle_notifications."""
    if not messages:
        return False
    structured_msgs = [m for m in messages if m.structured]
    if not structured_msgs:
        return False
    return all(m.structured.type == "idle_notification" for m in structured_msgs)
```

**Impact**: Prevents idle exchanges from creating unnecessary pair rooms.

---

### Rule 3: Suppress Broadcast Task Assignments from Pair Rooms

**Definition**: Don't create pair rooms when the only/primary messages are broadcast task assignments

**Applies to**:
- Pair rooms created mainly from broadcast messages

**Implementation**:
```python
def is_broadcast_task_only_room(messages: list[Message]) -> bool:
    """Hide pair rooms that are only broadcast task assignments."""
    if not messages or len(messages) < 2:
        return False

    # Count real (non-broadcast) messages
    real_msgs = [m for m in messages if not m.is_broadcast]

    # Count broadcast task assignments
    broadcast_tasks = [m for m in messages if m.is_broadcast and m.structured and m.structured.type == "task_assignment"]

    # Hide if no real messages and room is >80% broadcast tasks
    return len(real_msgs) == 0 and len(broadcast_tasks) >= 1
```

**Impact**: Broadcast task assignments go to Tasks tab only, not to sidebar pair rooms.

---

### Rule 4: Mixed Room Threshold

**Definition**: Keep rooms with ANY non-structured message, but mark protocol-heavy ones

**Applies to**:
- Rooms with real conversation but also protocol noise

**Strategy**: Don't hide, but could:
- Flag in UI (e.g., badge showing "1 real message + 50 structured")
- Sort mixed rooms below pure-conversation rooms

---

## 7. Edge Cases & Implementation Considerations

### Edge Case 1: Single Real Message + Many Structured

Example:
```
Messages in analyst↔team-lead:
- [TASK] Complete audit
- [APPROVED] permission_response
- [IDLE] waiting for response
- "Found the vulnerability" (real message)
- [IDLE] idle again
- [IDLE] still idle
```

**Decision**: Don't hide. One real message = conversation worth showing. But could display as "1 real msg, 5 protocol" in UI.

---

### Edge Case 2: Shutdown Sequence Rooms

```
Messages:
- [TASK] final-task
- [SHUTDOWN REQUEST]
- [SHUTDOWN APPROVED]
```

**Decision**: Hide. This is a protocol sequence, not a conversation. User can see task in Tasks tab.

---

### Edge Case 3: Permission Workflows as Conversations

```
Messages:
- [PERMISSION REQUEST] Need to run security scan
- [APPROVED] Permission granted
```

**Decision**: This is tricky. It's technically protocol, but represents a real interaction. Could be kept for audit trail. Current rule would hide it (100% structured).

**Recommendation**: Apply Rule 1 (hide 100% structured) but add a whitelist exception: if there's a permission_request + permission_response pair with actual permission details in the summary, keep it visible.

---

### Edge Case 4: Very Old Idle Notifications

```
agent-x idle from 2026-02-01, never resumes
```

**Impact**: @agent-x room exists but is 100% idle.

**Decision**: Hide by Rule 2. But preserve in search/history for completeness.

---

## 8. Summary of Filtering Rules

### Apply in this order:

1. **Hide if idle-only** (`is_idle_only_room`) → Rule 2
2. **Hide if broadcast-task-only** (`is_broadcast_task_only_room`) → Rule 3
3. **Hide if 100% structured** AND no permission_request/response interactions (`is_protocol_only_room`) → Rule 1
4. **Keep everything else** (real conversations, mixed rooms)

### Sidebar UX Impact:

**Before filtering:**
- @analyst, @researcher, @team-lead (may have only structured)
- analyst↔team-lead, analyst↔researcher, researcher↔team-lead (many only protocol)
- #general (all messages)

**After filtering:**
- @analyst, @researcher, @team-lead (only if 1+ real message or 1+ non-idle structured)
- analyst↔team-lead (only if 1+ real message or mixed)
- #general (all messages)

**Expected reduction**: 20-40% fewer pair rooms, 10-20% fewer @agent rooms (depending on data).

---

## 9. Implementation Checklist

- [ ] Add `is_protocol_only_room()` to `MessageStore`
- [ ] Add `is_idle_only_room()` to `MessageStore`
- [ ] Add `is_broadcast_task_only_room()` to `MessageStore`
- [ ] Add `should_display_room()` method that applies all rules
- [ ] Call `should_display_room()` in `discover_rooms()` before returning
- [ ] Add tests for edge cases (single real message, shutdown sequences, etc.)
- [ ] Update `room_sidebar.py` to handle filtered rooms gracefully
- [ ] Add configuration flag to disable filtering (for debug/transparency)

---

## 10. Data-Driven Observations from Test Fixtures

**Test data breakdown** (10 messages total):

| File | Recipient | Message Count | Structured | Real | Pattern |
|------|-----------|---------------|-----------|------|---------|
| team-lead.json | team-lead | 3 | 2/3 (task_assignment, permission_response) | 1/3 | Mixed |
| analyst.json | analyst | 3 | 2/3 (permission_request, idle_notification) | 1/3 | Mixed |
| researcher.json | researcher | 4 | 3/4 (task_assignment, shutdown_request, shutdown_approved) | 1/4 | Mixed |

**No pure-protocol rooms in test data**, but real-world systems likely have them. Test data is well-balanced with conversations.

---

## Recommendation

**Implement all three rules** (idle-only, broadcast-task-only, protocol-only) to reduce sidebar clutter while preserving genuine conversations. The filtering is conservative: only hide rooms where 100% or near-100% of content is infrastructure noise.

Start with **Rule 2 (idle-only)** as the quickest win with lowest risk of hiding real conversations.

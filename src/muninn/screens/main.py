from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import (
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from muninn.models.room import Room, RoomType
from muninn.models.team import TeamConfig
from muninn.screens.help import HelpScreen
from muninn.services.color_manager import ColorManager
from muninn.services.message_store import MessageStore
from muninn.services.team_discovery import load_team_config
from muninn.services.watcher import InboxFileChanged, NewInboxFile, ConfigChanged
from muninn.widgets.command_bar import CommandBar
from muninn.widgets.message_list import MessageList
from muninn.widgets.room_sidebar import RoomSidebar, RoomSelected
from muninn.widgets.task_card import TaskCard


class MainScreen(Screen[None]):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "tab_messages", "Messages", show=True),
        Binding("2", "tab_tasks", "Tasks", show=True),
        Binding("3", "tab_team", "Team", show=True),
        Binding("p", "toggle_permissions", "Toggle Perms", show=True),
        Binding("o", "toggle_protocol", "Toggle Protocol", show=True),
        # Panel focus
        Binding("h", "focus_sidebar", "Sidebar", show=False),
        Binding("l", "focus_content", "Content", show=False),
        # Vim motions
        Binding("j", "scroll_down_line", "Down", show=False),
        Binding("k", "scroll_up_line", "Up", show=False),
        Binding("G", "scroll_to_end", "Bottom", show=False),
        Binding("g", "g_pressed", "Top", show=False),
        Binding("ctrl+d", "half_page_down", show=False),
        Binding("ctrl+u", "half_page_up", show=False),
        Binding("ctrl+f", "full_page_down", show=False),
        Binding("ctrl+b", "full_page_up", show=False),
        # Search
        Binding("slash", "open_search", "Search", show=False),
        Binding("n", "search_next", show=False),
        Binding("N", "search_prev", show=False),
        # Command mode
        Binding("colon", "open_command", show=False),
        # Help
        Binding("question_mark", "show_help", "?Help", show=False),
    ]

    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }
    #main-content {
        height: 1fr;
    }
    #status-bar {
        height: 1;
        dock: bottom;
        background: $accent;
        padding: 0 1;
    }
    #messages-pane-content {
        layout: horizontal;
        height: 1fr;
    }
    """

    def __init__(
        self,
        team_path: Path,
        team_config: TeamConfig | None = None,
    ) -> None:
        super().__init__()
        self._team_path = team_path
        self._team_config = team_config
        self._store = MessageStore()
        self._color_mgr = ColorManager()
        self._current_room: Room | None = None
        self._rooms: list[Room] = []
        self._filter_permissions = False
        self._filter_protocol = False
        # gg state machine
        self._g_pending = False
        self._g_timer: Timer | None = None
        # Search state
        self._search_query = ""
        self._search_matches: list[int] = []
        self._search_match_idx = -1

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            with TabPane("Messages", id="messages-tab"):
                with Horizontal(id="messages-pane-content"):
                    lead = self._team_config.lead_agent_id if self._team_config else None
                    yield RoomSidebar([], lead_agent_id=lead, id="sidebar")
                    yield MessageList(id="message-list")
            with TabPane("Tasks", id="tasks-tab"):
                yield VerticalScroll(id="tasks-list")
            with TabPane("Team", id="team-tab"):
                yield VerticalScroll(id="team-info")
        yield Static("", id="status-bar")
        yield CommandBar(id="command-bar")
        yield Footer()

    def on_mount(self) -> None:
        if self._team_config is None:
            self._team_config = load_team_config(self._team_path)

        inbox_dir = self._team_path / "inboxes"
        self._store.load_all_inboxes(inbox_dir)
        self._color_mgr.assign_initial(sorted(self._store.known_agents))

        self._rooms = self._store.discover_rooms(filter_protocol=self._filter_protocol)
        self._update_sidebar()

        if self._rooms:
            self._current_room = self._rooms[0]
            self._refresh_messages()

        self._update_status_bar()
        self._load_tasks()
        self._load_team_info()
        self._start_watcher()

    def _start_watcher(self) -> None:
        from muninn.services.watcher import watch_team_dir

        self.run_worker(watch_team_dir(self._team_path, self), thread=False)

    def _update_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", RoomSidebar)
        sidebar.update_rooms(self._rooms)

    def _refresh_messages(self) -> None:
        if not self._current_room:
            return
        msg_list = self.query_one("#message-list", MessageList)
        messages = self._store.get_messages(self._current_room)
        show_recipient = self._current_room.room_type == RoomType.GENERAL
        msg_list.load_messages(
            messages,
            self._color_mgr.get_color,
            show_recipient=show_recipient,
            filter_permissions=self._filter_permissions,
        )

    def _update_status_bar(self) -> None:
        bar = self.query_one("#status-bar", Static)
        name = self._team_config.name if self._team_config else "unknown"
        agents = len(self._store.known_agents)
        total = self._store.total_count
        perm_status = " | perms hidden" if self._filter_permissions else ""
        proto_status = " | protocol hidden" if self._filter_protocol else ""
        search_status = ""
        if self._search_query:
            idx = self._search_match_idx + 1 if self._search_matches else 0
            count = len(self._search_matches)
            search_status = f" | /{self._search_query} [{idx}/{count}]"
        bar.update(
            f" {name} | {agents} agents | {total} messages{perm_status}{proto_status}{search_status}"
        )

    def _load_tasks(self) -> None:
        tasks_container = self.query_one("#tasks-list", VerticalScroll)
        tasks = self._store.extract_tasks()
        if tasks:
            for task in tasks:
                _ = tasks_container.mount(TaskCard(task))
        else:
            _ = tasks_container.mount(Static("No tasks found."))

    def _load_team_info(self) -> None:
        info = self.query_one("#team-info", VerticalScroll)
        if self._team_config:
            cfg = self._team_config
            _ = info.mount(Static(f"[bold]Team:[/] {cfg.name}"))
            _ = info.mount(Static(f"[bold]Description:[/] {cfg.description}"))
            _ = info.mount(Static(f"[bold]Created:[/] {cfg.created_at}"))
            _ = info.mount(Static(f"[bold]Lead:[/] {cfg.lead_agent_id}"))
            _ = info.mount(Static(""))
            _ = info.mount(Static("[bold underline]Config Members[/]"))
            for m in cfg.members:
                _ = info.mount(Static(f"  {m.name} ({m.agent_type}) — {m.model}"))
                _ = info.mount(Static(f"    cwd: {m.cwd}"))

        config_agents: set[str] = (
            {m.name for m in self._team_config.members} if self._team_config else set()
        )
        discovered = self._store.known_agents - config_agents
        if discovered:
            _ = info.mount(Static(""))
            _ = info.mount(
                Static("[bold underline]Discovered Agents (not in config)[/]")
            )
            for agent in sorted(discovered):
                _ = info.mount(Static(f"  {agent}"))

    # --- Scroll helpers ---

    def _get_active_tab(self) -> str:
        tabs = self.query_one("#tabs", TabbedContent)
        return tabs.active or "messages-tab"

    def _get_scroll_target(self) -> VerticalScroll | Tree | None:
        """Return the most appropriate scrollable for the current context."""
        focused = self.focused
        # If a Tree is focused, use it directly
        if isinstance(focused, Tree):
            return focused
        # Otherwise, return the scrollable for the active tab
        active = self._get_active_tab()
        if active == "messages-tab":
            return self.query_one("#message-list", MessageList)
        elif active == "tasks-tab":
            return self.query_one("#tasks-list", VerticalScroll)
        elif active == "team-tab":
            return self.query_one("#team-info", VerticalScroll)
        return None

    # --- Panel focus actions ---

    def action_focus_sidebar(self) -> None:
        active = self._get_active_tab()
        if active == "messages-tab":
            try:
                tree = self.query_one("#room-tree", Tree)
                tree.focus()
            except Exception:
                pass

    def action_focus_content(self) -> None:
        active = self._get_active_tab()
        if active == "messages-tab":
            self.query_one("#message-list", MessageList).focus()
        elif active == "tasks-tab":
            self.query_one("#tasks-list", VerticalScroll).focus()
        elif active == "team-tab":
            self.query_one("#team-info", VerticalScroll).focus()

    # --- Vim motion actions ---

    def action_scroll_down_line(self) -> None:
        target = self._get_scroll_target()
        if isinstance(target, Tree):
            target.action_cursor_down()
        elif isinstance(target, VerticalScroll):
            target.scroll_relative(y=1, animate=False)

    def action_scroll_up_line(self) -> None:
        target = self._get_scroll_target()
        if isinstance(target, Tree):
            target.action_cursor_up()
        elif isinstance(target, VerticalScroll):
            target.scroll_relative(y=-1, animate=False)

    def action_scroll_to_end(self) -> None:
        self._cancel_g()
        target = self._get_scroll_target()
        if isinstance(target, Tree):
            target.scroll_end(animate=False)
        elif isinstance(target, VerticalScroll):
            target.scroll_end(animate=False)

    def action_g_pressed(self) -> None:
        if self._g_pending:
            # Second g — scroll to top
            self._cancel_g()
            target = self._get_scroll_target()
            if isinstance(target, Tree):
                target.scroll_home(animate=False)
            elif isinstance(target, VerticalScroll):
                target.scroll_home(animate=False)
        else:
            self._g_pending = True
            self._g_timer = self.set_timer(0.5, self._g_timeout)

    def _g_timeout(self) -> None:
        self._g_pending = False
        self._g_timer = None

    def _cancel_g(self) -> None:
        self._g_pending = False
        if self._g_timer is not None:
            self._g_timer.stop()
            self._g_timer = None

    def action_half_page_down(self) -> None:
        target = self._get_scroll_target()
        if isinstance(target, VerticalScroll):
            target.scroll_relative(y=target.size.height // 2, animate=False)

    def action_half_page_up(self) -> None:
        target = self._get_scroll_target()
        if isinstance(target, VerticalScroll):
            target.scroll_relative(y=-(target.size.height // 2), animate=False)

    def action_full_page_down(self) -> None:
        target = self._get_scroll_target()
        if isinstance(target, VerticalScroll):
            target.scroll_page_down(animate=False)

    def action_full_page_up(self) -> None:
        target = self._get_scroll_target()
        if isinstance(target, VerticalScroll):
            target.scroll_page_up(animate=False)

    # --- Search actions ---

    def action_open_search(self) -> None:
        self.query_one("#command-bar", CommandBar).show("/")

    def action_search_next(self) -> None:
        if not self._search_matches:
            return
        self._search_match_idx = (self._search_match_idx + 1) % len(
            self._search_matches
        )
        self._scroll_to_match()

    def action_search_prev(self) -> None:
        if not self._search_matches:
            return
        self._search_match_idx = (self._search_match_idx - 1) % len(
            self._search_matches
        )
        self._scroll_to_match()

    def _execute_search(self, query: str) -> None:
        self._search_query = query
        msg_list = self.query_one("#message-list", MessageList)
        self._search_matches = msg_list.find_matches(query)
        if self._search_matches:
            self._search_match_idx = 0
            self._scroll_to_match()
        else:
            self._search_match_idx = -1
        self._update_status_bar()

    def _scroll_to_match(self) -> None:
        if not self._search_matches or self._search_match_idx < 0:
            return
        msg_idx = self._search_matches[self._search_match_idx]
        msg_list = self.query_one("#message-list", MessageList)
        msg_list.highlight_match(msg_idx)
        self._update_status_bar()

    def _clear_search(self) -> None:
        self._search_query = ""
        self._search_matches = []
        self._search_match_idx = -1
        self._update_status_bar()

    # --- Command mode ---

    def action_open_command(self) -> None:
        self.query_one("#command-bar", CommandBar).show(":")

    def _execute_command(self, cmd: str) -> None:
        if cmd in ("q", "quit"):
            self.app.exit()
        elif cmd in ("h", "help"):
            self.app.push_screen(HelpScreen())

    # --- Help ---

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

    # --- CommandBar events ---

    def on_command_bar_submitted(self, event: CommandBar.Submitted) -> None:
        if event.mode == "/":
            self._execute_search(event.value)
        elif event.mode == ":":
            self._execute_command(event.value)

    def on_command_bar_dismissed(self, event: CommandBar.Dismissed) -> None:
        if event.mode == "/":
            self._clear_search()

    # --- Event handlers ---

    def on_room_selected(self, event: RoomSelected) -> None:
        self._current_room = event.room
        self._refresh_messages()

    def action_tab_messages(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "messages-tab"

    def action_tab_tasks(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tasks-tab"

    def action_tab_team(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "team-tab"

    def action_toggle_permissions(self) -> None:
        self._filter_permissions = not self._filter_permissions
        self._refresh_messages()
        self._update_status_bar()

    def action_toggle_protocol(self) -> None:
        self._filter_protocol = not self._filter_protocol
        self._rooms = self._store.discover_rooms(filter_protocol=self._filter_protocol)
        self._update_sidebar()
        self._update_status_bar()

    def action_quit(self) -> None:
        self.app.exit()

    # --- Watcher message handlers ---

    def on_inbox_file_changed(self, event: InboxFileChanged) -> None:
        new_msgs = self._store.load_inbox_file(event.path)
        if new_msgs:
            for msg in new_msgs:
                _ = self._color_mgr.get_color(msg.sender)
            self._rooms = self._store.discover_rooms(filter_protocol=self._filter_protocol)
            self._update_sidebar()
            if self._current_room:
                msg_list = self.query_one("#message-list", MessageList)
                show_recipient = self._current_room.room_type == RoomType.GENERAL
                for msg in new_msgs:
                    if self._current_room.matches_message(msg.sender, msg.recipient):
                        if (
                            self._filter_permissions
                            and msg.structured
                            and msg.structured.type
                            in ("permission_request", "permission_response")
                        ):
                            continue
                        msg_list.append_message(
                            msg,
                            self._color_mgr.get_color(msg.sender),
                            show_recipient=show_recipient,
                        )
            self._update_status_bar()

    def on_new_inbox_file(self, event: NewInboxFile) -> None:
        new_msgs = self._store.load_inbox_file(event.path)
        if new_msgs:
            for msg in new_msgs:
                _ = self._color_mgr.get_color(msg.sender)
            self._rooms = self._store.discover_rooms(filter_protocol=self._filter_protocol)
            self._update_sidebar()
            self._update_status_bar()

    def on_config_changed(self, event: ConfigChanged) -> None:
        self._team_config = load_team_config(self._team_path)

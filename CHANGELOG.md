# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-16

### Added

- Waiting screen when no teams are discovered, with automatic polling
- Sidebar rooms grouped by team lead, conversations, and `#general` at root
- Protocol-only room filtering with `o` toggle keybinding
- Dim styling for protocol-heavy rooms (>80% structured messages)
- Pair room name truncation to fit sidebar width (10 char cap per agent)

### Changed

- Removed redundant `@agent` inbox rooms — messages now shown only in pair rooms
- Renamed sidebar sections: "GROUP"/"DIRECT" replaced with "TEAM LEAD"/"CONVERSATIONS"
- Lowered pair room threshold from 2 messages to 1
- Broadcast messages excluded from pair room unread counts

### Fixed

- `q` keybinding on WaitingScreen now exits correctly

## [0.1.0] - 2026-03-14

### Added

- Multi-room message viewer for `#general`, per-agent, and pair conversations
- Task tracking with structured cards showing status, assignee, and focus areas
- Team overview panel with configuration and member roles
- Live filesystem watching for real-time message updates
- Full-text search with `/` and `n`/`N` navigation
- Vim-style keybindings (`hjkl`, `gg`/`G`, `Ctrl+d`/`Ctrl+u`)
- Color-coded agent messages for visual scanning
- Permission message filtering toggle (`p`)
- Structured parsing for permission requests, task assignments, shutdown events, and idle notifications
- CLI with `--team`, `--path`, and `--teams-dir` options
- Team auto-discovery from `~/.claude/teams`

[Unreleased]: https://github.com/grimmy0/muninn/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/grimmy0/muninn/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/grimmy0/muninn/releases/tag/v0.1.0

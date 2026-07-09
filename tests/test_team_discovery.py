from muninn.services.team_discovery import (
    discover_agents_from_inboxes,
    load_team_config,
    discover_teams,
)


class TestTeamDiscovery:
    def test_load_team_config(self, team_path):
        config = load_team_config(team_path)
        assert config is not None
        assert config.name == "test-team"
        assert len(config.members) == 1
        assert config.members[0].name == "team-lead"

    def test_discover_agents_from_inboxes(self, team_path):
        agents = discover_agents_from_inboxes(team_path)
        assert len(agents) == 3
        assert "team-lead" in agents
        assert "analyst" in agents
        assert "researcher" in agents

    def test_config_vs_inboxes_mismatch(self, team_path):
        config = load_team_config(team_path)
        assert config is not None
        agents = discover_agents_from_inboxes(team_path)
        config_agents = {m.name for m in config.members}
        orphaned = agents - config_agents
        # Config has 1 member but 3 inboxes — 2 orphaned
        assert len(orphaned) == 2

    def test_is_safe_path_valid(self, tmp_path):
        from muninn.services.team_discovery import is_safe_path
        base = tmp_path / "teams"
        base.mkdir()
        team = base / "my-team"
        team.mkdir()
        assert is_safe_path(team, base) is True

    def test_is_safe_path_traversal(self, tmp_path):
        from muninn.services.team_discovery import is_safe_path
        base = tmp_path / "teams"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        assert is_safe_path(outside, base) is False

    def test_is_safe_path_symlink(self, tmp_path):
        from muninn.services.team_discovery import is_safe_path
        base = tmp_path / "teams"
        base.mkdir()
        target = tmp_path / "target"
        target.mkdir()
        sym = base / "sym-team"
        sym.symlink_to(target, target_is_directory=True)
        assert is_safe_path(sym, base) is False

    def test_discover_teams_ignores_symlinks(self, tmp_path):
        import json

        # 1. Create a valid team
        valid_team = tmp_path / "valid-team"
        valid_team.mkdir()
        (valid_team / "config.json").write_text(json.dumps({"name": "valid", "members": []}))

        # 2. Create a symlinked team
        target_dir = tmp_path.parent / "target-outside"
        target_dir.mkdir(exist_ok=True)
        (target_dir / "config.json").write_text(json.dumps({"name": "symlinked", "members": []}))
        sym_team = tmp_path / "sym-team"
        sym_team.symlink_to(target_dir, target_is_directory=True)

        # 3. Discover teams
        teams = discover_teams(tmp_path)
        # Should only discover the valid team, NOT the symlinked one!
        assert len(teams) == 1
        assert teams[0][1].name == "valid"


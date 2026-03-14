
from muninn.services.team_discovery import (
    discover_agents_from_inboxes,
    load_team_config,
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

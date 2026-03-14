from __future__ import annotations

PALETTE: list[str] = [
    "#61afef",  # blue
    "#e06c75",  # red
    "#98c379",  # green
    "#e5c07b",  # yellow
    "#c678dd",  # purple
    "#56b6c2",  # cyan
    "#d19a66",  # orange
    "#be5046",  # dark red
    "#7ec8e3",  # light blue
    "#c3e88d",  # light green
]


class ColorManager:
    def __init__(self) -> None:
        self._assignments: dict[str, str] = {}
        self._next_idx = 0

    def assign_initial(self, agents: list[str]) -> None:
        for agent in sorted(agents):
            if agent not in self._assignments:
                self._assignments[agent] = PALETTE[self._next_idx % len(PALETTE)]
                self._next_idx += 1

    def get_color(self, agent: str) -> str:
        if agent not in self._assignments:
            self._assignments[agent] = PALETTE[self._next_idx % len(PALETTE)]
            self._next_idx += 1
        return self._assignments[agent]

    @property
    def assignments(self) -> dict[str, str]:
        return dict(self._assignments)

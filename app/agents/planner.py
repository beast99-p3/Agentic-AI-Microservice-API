from __future__ import annotations


class Planner:
    """Lightweight planner hints for ambiguous tasks.

    The runtime still relies on model reasoning; this class adds deterministic
    scaffolding instructions so the agent consistently decomposes fuzzy tasks.
    """

    def build_planning_hint(self, task: str) -> str:
        return (
            "Planning hint for the task:\n"
            "- Identify the objective and constraints.\n"
            "- If ambiguous, make explicit assumptions.\n"
            "- Break work into 2-5 actionable substeps.\n"
            "- Decide whether tools are needed for each substep.\n"
            f"Task: {task}"
        )

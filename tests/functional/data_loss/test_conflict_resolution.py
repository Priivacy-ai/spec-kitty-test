"""
Conflict resolution tests (WP09: T053).

Tests for:
- Lane conflicts: more-done lane wins
- Checkbox conflicts: checked wins over unchecked
- History conflicts: chronological concatenation with deduplication

These tests ensure merge conflicts in status files are resolved
in ways that preserve progress information and never lose work.
"""
import pytest
from datetime import datetime
from typing import List, Dict, Any


# =============================================================================
# Lane Conflict Resolution
# =============================================================================

# Lane precedence: done > for_review > doing > planned
LANE_PRECEDENCE = {
    "planned": 0,
    "doing": 1,
    "for_review": 2,
    "done": 3
}


def resolve_lane_conflict(base_lane: str, ours_lane: str, theirs_lane: str) -> str:
    """
    Resolve lane conflicts using more-done-wins rule.

    Args:
        base_lane: Original lane before divergence
        ours_lane: Our branch's lane value
        theirs_lane: Their branch's lane value

    Returns:
        Resolved lane (the more-done one)
    """
    ours_precedence = LANE_PRECEDENCE.get(ours_lane, 0)
    theirs_precedence = LANE_PRECEDENCE.get(theirs_lane, 0)

    return ours_lane if ours_precedence >= theirs_precedence else theirs_lane


def resolve_checkbox_conflict(
    base_state: bool,
    ours_state: bool,
    theirs_state: bool
) -> bool:
    """
    Resolve checkbox conflicts using checked-wins rule.

    Args:
        base_state: Original checkbox state
        ours_state: Our branch's checkbox state (True = [x])
        theirs_state: Their branch's checkbox state

    Returns:
        Resolved state (True if either is checked)
    """
    return ours_state or theirs_state


def merge_history(
    ours_history: List[Dict[str, Any]],
    theirs_history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge history entries chronologically with deduplication.

    Args:
        ours_history: Our branch's history entries
        theirs_history: Their branch's history entries

    Returns:
        Merged history sorted by timestamp, duplicates removed
    """
    # Combine all entries
    all_entries = ours_history + theirs_history

    # Deduplicate by creating a key from timestamp + action
    seen = set()
    unique_entries = []

    for entry in all_entries:
        # Create key for deduplication
        key = (entry.get("timestamp", ""), entry.get("action", ""))
        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    # Sort by timestamp
    def get_timestamp(entry: Dict) -> str:
        return entry.get("timestamp", "")

    unique_entries.sort(key=get_timestamp)

    return unique_entries


class TestLaneConflictResolution:
    """Test lane conflict resolution: more-done wins."""

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_lane_conflict_more_done_wins(self, conflict_scenario_factory):
        """Lane conflicts resolve to more-done status."""
        # Create conflict scenario
        scenario = conflict_scenario_factory("status")

        # WP01 says "done", WP02 says "for_review"
        scenario.add_modification(
            "WP01",
            "tasks/WP01.md",
            {"lane": "done"}
        )
        scenario.add_modification(
            "WP02",
            "tasks/WP01.md",
            {"lane": "for_review"}
        )
        scenario.expected_resolution = "done"

        # Resolve conflict
        resolved = resolve_lane_conflict(
            base_lane="planned",
            ours_lane="done",
            theirs_lane="for_review"
        )

        assert resolved == "done", "More-done lane should win"

    @pytest.mark.functional
    @pytest.mark.data_loss
    @pytest.mark.parametrize("lane1,lane2,expected", [
        ("planned", "doing", "doing"),
        ("doing", "for_review", "for_review"),
        ("for_review", "done", "done"),
        ("planned", "done", "done"),
        ("doing", "done", "done"),
        ("planned", "for_review", "for_review"),
    ])
    def test_lane_precedence_order(self, lane1, lane2, expected):
        """Lane precedence: done > for_review > doing > planned."""
        resolved = resolve_lane_conflict("planned", lane1, lane2)
        assert resolved == expected

    @pytest.mark.functional
    @pytest.mark.data_loss
    @pytest.mark.parametrize("lane1,lane2,expected", [
        # Symmetric tests - order shouldn't matter
        ("doing", "planned", "doing"),
        ("for_review", "doing", "for_review"),
        ("done", "for_review", "done"),
        ("done", "planned", "done"),
        ("done", "doing", "done"),
        ("for_review", "planned", "for_review"),
    ])
    def test_lane_precedence_symmetric(self, lane1, lane2, expected):
        """Lane resolution is symmetric (order doesn't matter)."""
        # Test both orderings
        resolved1 = resolve_lane_conflict("planned", lane1, lane2)
        resolved2 = resolve_lane_conflict("planned", lane2, lane1)

        assert resolved1 == expected
        assert resolved2 == expected

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_same_lane_no_conflict(self):
        """Same lane values don't conflict."""
        for lane in ["planned", "doing", "for_review", "done"]:
            resolved = resolve_lane_conflict("planned", lane, lane)
            assert resolved == lane

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_unknown_lane_treated_as_lowest(self):
        """Unknown lane values treated as lowest precedence."""
        resolved = resolve_lane_conflict("planned", "unknown", "doing")
        assert resolved == "doing"

        resolved = resolve_lane_conflict("planned", "doing", "invalid")
        assert resolved == "doing"


class TestCheckboxConflictResolution:
    """Test checkbox conflict resolution: checked wins."""

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_checkbox_conflict_checked_wins_ours(self):
        """Checked checkbox wins when ours is checked."""
        resolved = resolve_checkbox_conflict(
            base_state=False,
            ours_state=True,   # [x]
            theirs_state=False  # [ ]
        )
        assert resolved is True, "Checked checkbox should win"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_checkbox_conflict_checked_wins_theirs(self):
        """Checked checkbox wins when theirs is checked."""
        resolved = resolve_checkbox_conflict(
            base_state=False,
            ours_state=False,  # [ ]
            theirs_state=True  # [x]
        )
        assert resolved is True, "Checked checkbox should win"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_checkbox_both_checked_stays_checked(self):
        """Both checked results in checked (no real conflict)."""
        resolved = resolve_checkbox_conflict(
            base_state=False,
            ours_state=True,
            theirs_state=True
        )
        assert resolved is True

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_checkbox_both_unchecked_stays_unchecked(self):
        """Both unchecked results in unchecked (no real conflict)."""
        resolved = resolve_checkbox_conflict(
            base_state=False,
            ours_state=False,
            theirs_state=False
        )
        assert resolved is False

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_checkbox_unchecking_not_allowed(self):
        """Once checked, can't be unchecked (checked wins over uncheck attempt)."""
        # Base was checked, theirs tries to uncheck
        resolved = resolve_checkbox_conflict(
            base_state=True,
            ours_state=True,   # Keep checked
            theirs_state=False  # Try to uncheck
        )
        assert resolved is True, "Can't uncheck - checked wins"

    @pytest.mark.functional
    @pytest.mark.data_loss
    @pytest.mark.parametrize("ours,theirs,expected", [
        (True, False, True),
        (False, True, True),
        (True, True, True),
        (False, False, False),
    ])
    def test_checkbox_all_combinations(self, ours, theirs, expected):
        """Test all checkbox state combinations."""
        resolved = resolve_checkbox_conflict(False, ours, theirs)
        assert resolved == expected


class TestHistoryMerging:
    """Test history concatenation: chronological order with deduplication."""

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_concatenates_chronologically(self):
        """History conflicts concatenate in chronological order."""
        ours_history = [
            {
                "timestamp": "2026-01-23T10:00:00Z",
                "lane": "planned",
                "agent": "system",
                "action": "Created"
            },
            {
                "timestamp": "2026-01-23T11:00:00Z",
                "lane": "doing",
                "agent": "claude",
                "action": "Started"
            }
        ]

        theirs_history = [
            {
                "timestamp": "2026-01-23T10:00:00Z",
                "lane": "planned",
                "agent": "system",
                "action": "Created"
            },
            {
                "timestamp": "2026-01-23T12:00:00Z",
                "lane": "for_review",
                "agent": "codex",
                "action": "Completed"
            }
        ]

        merged = merge_history(ours_history, theirs_history)

        # Should have all unique entries, sorted by timestamp
        assert len(merged) == 3  # Duplicate "Created" removed
        assert merged[0]["action"] == "Created"
        assert merged[1]["action"] == "Started"
        assert merged[2]["action"] == "Completed"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_deduplicates_identical_entries(self):
        """Identical history entries are deduplicated."""
        ours = [{"timestamp": "2026-01-23T10:00:00Z", "action": "Created"}]
        theirs = [{"timestamp": "2026-01-23T10:00:00Z", "action": "Created"}]

        merged = merge_history(ours, theirs)
        assert len(merged) == 1, "Duplicate entry should be removed"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_preserves_all_unique_entries(self):
        """All unique history entries are preserved."""
        ours = [
            {"timestamp": "2026-01-23T10:00:00Z", "action": "Action A"},
            {"timestamp": "2026-01-23T11:00:00Z", "action": "Action B"},
        ]
        theirs = [
            {"timestamp": "2026-01-23T10:30:00Z", "action": "Action C"},
            {"timestamp": "2026-01-23T11:30:00Z", "action": "Action D"},
        ]

        merged = merge_history(ours, theirs)

        # All 4 unique entries preserved
        assert len(merged) == 4
        actions = [e["action"] for e in merged]
        assert "Action A" in actions
        assert "Action B" in actions
        assert "Action C" in actions
        assert "Action D" in actions

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_sorted_by_timestamp(self):
        """Merged history is sorted by timestamp."""
        ours = [
            {"timestamp": "2026-01-23T12:00:00Z", "action": "Later"},
        ]
        theirs = [
            {"timestamp": "2026-01-23T10:00:00Z", "action": "Earlier"},
        ]

        merged = merge_history(ours, theirs)

        assert merged[0]["action"] == "Earlier"
        assert merged[1]["action"] == "Later"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_empty_ours(self):
        """Merge works with empty ours history."""
        ours = []
        theirs = [{"timestamp": "2026-01-23T10:00:00Z", "action": "Entry"}]

        merged = merge_history(ours, theirs)

        assert len(merged) == 1
        assert merged[0]["action"] == "Entry"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_empty_theirs(self):
        """Merge works with empty theirs history."""
        ours = [{"timestamp": "2026-01-23T10:00:00Z", "action": "Entry"}]
        theirs = []

        merged = merge_history(ours, theirs)

        assert len(merged) == 1
        assert merged[0]["action"] == "Entry"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_both_empty(self):
        """Merge works with both histories empty."""
        merged = merge_history([], [])
        assert merged == []

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_preserves_all_fields(self):
        """All fields in history entries are preserved."""
        entry = {
            "timestamp": "2026-01-23T10:00:00Z",
            "lane": "doing",
            "agent": "test-agent",
            "shell_pid": "12345",
            "action": "Test action",
            "custom_field": "custom_value"
        }

        merged = merge_history([entry], [])

        assert len(merged) == 1
        for key, value in entry.items():
            assert merged[0][key] == value

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_history_same_timestamp_different_action(self):
        """Same timestamp but different action are kept."""
        ours = [{"timestamp": "2026-01-23T10:00:00Z", "action": "Action A"}]
        theirs = [{"timestamp": "2026-01-23T10:00:00Z", "action": "Action B"}]

        merged = merge_history(ours, theirs)

        # Both entries have same timestamp but different actions
        # Both should be preserved
        assert len(merged) == 2
        actions = [e["action"] for e in merged]
        assert "Action A" in actions
        assert "Action B" in actions


class TestConflictScenarioFactory:
    """Test the conflict scenario factory fixture."""

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_factory_creates_scenario(self, conflict_scenario_factory):
        """Factory creates valid scenario object."""
        scenario = conflict_scenario_factory("status")

        assert scenario is not None
        assert scenario.conflict_type == "status"
        assert scenario.wp_modifications == {}
        assert scenario.auto_resolvable is True

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_factory_add_modification(self, conflict_scenario_factory):
        """Can add modifications to scenario."""
        scenario = conflict_scenario_factory("status")

        scenario.add_modification("WP01", "tasks.md", {"lane": "done"})
        scenario.add_modification("WP02", "tasks.md", {"lane": "doing"})

        assert "WP01" in scenario.wp_modifications
        assert "WP02" in scenario.wp_modifications
        assert scenario.wp_modifications["WP01"]["tasks.md"]["lane"] == "done"

    @pytest.mark.functional
    @pytest.mark.data_loss
    def test_factory_get_more_done_lane(self, conflict_scenario_factory):
        """ConflictScenario has correct lane precedence helper."""
        scenario_class = type(conflict_scenario_factory("status"))

        assert scenario_class.get_more_done_lane("planned", "done") == "done"
        assert scenario_class.get_more_done_lane("doing", "for_review") == "for_review"
        assert scenario_class.get_more_done_lane("done", "planned") == "done"

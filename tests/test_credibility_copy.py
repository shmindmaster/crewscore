"""Public copy must preserve CrewScore's written-control evidence boundary."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_comparison_describes_written_controls_not_production_harm():
    text = (REPO / "docs" / "comparison.md").read_text(encoding="utf-8").lower()
    assert "will this agent hurt someone in production" not in text
    assert "which published written controls does this system prompt not state" in text
    assert "not a prediction of runtime behavior" in text


def test_live_eval_guide_uses_selected_controls_not_an_arbitrary_score_gate():
    text = (REPO / "docs" / "next-steps-eval.md").read_text(encoding="utf-8").lower()
    assert "--threshold 50" not in text
    assert "--require human_gate.approval_required,safe_stop.stop_condition" in text
    assert "after selecting the written controls your product needs" in text

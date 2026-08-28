import pytest
from unittest.mock import patch, MagicMock
from src.schemas import FinalDecision, Verdict, Confidence, Recommendation
from src.decision_synthesizer import call_decision_synthesizer

@patch("src.decision_synthesizer.instructor.from_groq")
def test_call_decision_synthesizer_mocked(mock_from_groq):
    mock_client = MagicMock()
    mock_from_groq.return_value = mock_client
    
    mock_decision = FinalDecision(
        candidate_id="c1",
        recommendation=Recommendation.hire,
        confidence=Confidence.high,
        strengths=[],
        concerns=[],
        weighting_rationale=[],
        unresolved_disagreements=[]
    )
    mock_client.chat.completions.create.return_value = mock_decision
    
    decision = call_decision_synthesizer("JD text", {"agent": MagicMock()}, [], [])
    assert decision.recommendation == Recommendation.hire
    assert decision.confidence == Confidence.high

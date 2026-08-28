import pytest
from unittest.mock import patch, MagicMock
from src.schemas import AgentRole, CandidateProfile, AgentOpinion, Verdict, Confidence, FinalDecision, Recommendation
from src.orchestrator import run_pipeline

@patch("src.orchestrator.call_decision_synthesizer")
@patch("src.orchestrator.run_debate_turn")
@patch("src.orchestrator.detect_tensions")
@patch("src.orchestrator.verify_evidence")
@patch("src.orchestrator.call_agent")
@patch("src.orchestrator.build_profile")
def test_run_pipeline_mocked(mock_build, mock_call_agent, mock_verify, mock_detect, mock_debate, mock_synth):
    mock_build.return_value = CandidateProfile(
        candidate_id="c1", name="Test", target_role="Role", 
        identity_timeline=[], claimed_skills=[], quantifiable_claims=[], 
        behavioral_incidents=[], self_disclosed_gaps=[]
    )
    
    op = AgentOpinion(
        opinion_id="o1", agent_role=AgentRole.technical, candidate_id="c1", round=0, 
        verdict=Verdict.strong_hire, confidence=Confidence.high, evidence=[]
    )
    mock_call_agent.return_value = op
    mock_verify.return_value = op
    mock_detect.return_value = []
    
    mock_synth.return_value = FinalDecision(
        candidate_id="c1", recommendation=Recommendation.hire, confidence=Confidence.high,
        strengths=[], concerns=[], weighting_rationale=[], unresolved_disagreements=[]
    )
    
    report = run_pipeline("c1", "Test", "resume", "transcript", "jd")
    assert "Candidate Report — Test" in report
    assert "Recommendation: hire" in report

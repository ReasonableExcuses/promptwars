import pytest
from unittest.mock import patch, MagicMock
from src.schemas import Tension, TensionType, AgentRole, DebateTurn, AgentOpinion, Verdict, Confidence, ResponseType
from src.debate_engine import run_debate_turn, apply_revision

@patch("src.debate_engine.instructor.from_groq")
def test_run_debate_turn_mocked(mock_from_groq):
    mock_client = MagicMock()
    mock_from_groq.return_value = mock_client
    
    mock_turn = DebateTurn(
        turn_id="test_id",
        round=1,
        tension_id="t1",
        source_agent=AgentRole.technical,
        target_agent=AgentRole.culture,
        source_claim="Test claim",
        source_quote="Test quote",
        response_type=ResponseType.concede,
        response_evidence=[],
        prior_verdict=Verdict.strong_hire,
        new_verdict=Verdict.lean_hire,
        prior_confidence=Confidence.high,
        new_confidence=Confidence.medium
    )
    mock_client.chat.completions.create.return_value = mock_turn
    
    tension = Tension(
        tension_id="t1",
        tension_type=TensionType.contradiction,
        agent_a=AgentRole.technical,
        agent_b=AgentRole.culture,
        claim_a="Test claim",
        claim_b="Other claim",
        description="A contradiction"
    )
    
    opinions = {
        AgentRole.technical: AgentOpinion(
            opinion_id="o1",
            agent_role=AgentRole.technical,
            candidate_id="c1",
            round=0,
            verdict=Verdict.strong_hire,
            confidence=Confidence.high,
            evidence=[]
        ),
        AgentRole.culture: AgentOpinion(
            opinion_id="o2",
            agent_role=AgentRole.culture,
            candidate_id="c1",
            round=0,
            verdict=Verdict.strong_hire,
            confidence=Confidence.high,
            evidence=[]
        )
    }
    
    turn = run_debate_turn(tension, opinions, 1, AgentRole.culture, AgentRole.technical)
    assert turn.response_type == ResponseType.concede
    assert turn.new_verdict == Verdict.lean_hire

def test_apply_revision():
    op = AgentOpinion(
        opinion_id="o1",
        agent_role=AgentRole.culture,
        candidate_id="c1",
        round=0,
        verdict=Verdict.strong_hire,
        confidence=Confidence.high,
        evidence=[]
    )
    turn = DebateTurn(
        turn_id="test_id",
        round=1,
        tension_id="t1",
        source_agent=AgentRole.technical,
        target_agent=AgentRole.culture,
        source_claim="Test",
        source_quote="Test",
        response_type=ResponseType.concede,
        response_evidence=[],
        prior_verdict=Verdict.strong_hire,
        new_verdict=Verdict.lean_hire,
        prior_confidence=Confidence.high,
        new_confidence=Confidence.medium
    )
    new_op = apply_revision(op, turn)
    assert new_op.verdict == Verdict.lean_hire
    assert new_op.confidence == Confidence.medium
    assert new_op.round == 1

import pytest
from src.schemas import AgentOpinion, AgentRole, Verdict, Confidence, EvidenceItem, SourceDoc
from src.evidence_verifier import verify_evidence, normalize_whitespace

def test_normalize_whitespace():
    assert normalize_whitespace("This \n is \t a   test.") == "This is a test."

def test_verify_evidence_exact_match():
    opinion = AgentOpinion(
        opinion_id="1",
        agent_role=AgentRole.technical,
        candidate_id="A",
        round=0,
        verdict=Verdict.hire,
        confidence=Confidence.high,
        confidence_rationale="test",
        evidence=[
            EvidenceItem(claim="Test", quote="This is an EXACT match.", source=SourceDoc.resume, interpretation="test")
        ],
        open_questions=[],
        insufficient_info_flags=[]
    )
    source_text = "Some intro text. This is an EXACT match. Some outro text."
    result = verify_evidence(opinion, source_text)
    assert result.evidence[0].verified is True

def test_verify_evidence_fuzzy_match():
    opinion = AgentOpinion(
        opinion_id="1",
        agent_role=AgentRole.technical,
        candidate_id="A",
        round=0,
        verdict=Verdict.hire,
        confidence=Confidence.high,
        confidence_rationale="test",
        evidence=[
            EvidenceItem(claim="Test", quote="This is a minor typo match.", source=SourceDoc.resume, interpretation="test")
        ],
        open_questions=[],
        insufficient_info_flags=[]
    )
    # 1 char difference "minor typo match." vs "minor tpo match."
    # Thefuzz ratio should be > 92
    source_text = "Some intro text. This is a minor tpo match. Some outro text."
    
    # Let's check if the logic holds
    result = verify_evidence(opinion, source_text)
    assert result.evidence[0].verified is True

def test_verify_evidence_fails_fabricated():
    opinion = AgentOpinion(
        opinion_id="1",
        agent_role=AgentRole.technical,
        candidate_id="A",
        round=0,
        verdict=Verdict.hire,
        confidence=Confidence.high,
        confidence_rationale="test",
        evidence=[
            EvidenceItem(claim="Test", quote="I am a fabricated quote that does not exist.", source=SourceDoc.resume, interpretation="test")
        ],
        open_questions=[],
        insufficient_info_flags=[]
    )
    source_text = "Some intro text. Some outro text."
    result = verify_evidence(opinion, source_text)
    assert result.evidence[0].verified is False

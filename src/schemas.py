from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class VerificationStatus(str, Enum):
    verified = "verified"                    # formally measured
    self_reported_informal = "self_reported_informal"  # candidate admits it's informal
    unverified = "unverified"                # claimed, no verification method given

class SourceDoc(str, Enum):
    resume = "resume"
    transcript = "transcript"

class RoleEntry(BaseModel):
    title: str
    company: str
    start: str          # "YYYY-MM"
    end: Optional[str]  # None if current
    duration_months: int
    is_current: bool

class SkillClaim(BaseModel):
    skill: str
    source: SourceDoc
    quote: str
    location_hint: str   # e.g. "Skills section" or "A3"

class QuantClaim(BaseModel):
    metric: str                          # e.g. "~40% accuracy improvement"
    verification_status: VerificationStatus
    source_quote: str
    source: SourceDoc

class GapClaim(BaseModel):
    gap: str
    self_disclosed: bool                 # True if candidate volunteered it unprompted
    quote: str
    context: str                         # e.g. "Q3 technical section"

class Incident(BaseModel):
    summary: str
    root_cause_admission: bool           # did the candidate own the mistake directly?
    corrective_action: Optional[str]
    quote: str

class CandidateProfile(BaseModel):
    candidate_id: str
    name: str
    target_role: str
    identity_timeline: list[RoleEntry]
    claimed_skills: list[SkillClaim]
    quantifiable_claims: list[QuantClaim]
    self_disclosed_gaps: list[GapClaim]
    behavioral_incidents: list[Incident]

class Verdict(str, Enum):
    strong_hire = "strong_hire"
    hire = "hire"
    lean_hire = "lean_hire"
    lean_no_hire = "lean_no_hire"
    no_hire = "no_hire"
    insufficient_data = "insufficient_data"

class Confidence(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class EvidenceItem(BaseModel):
    claim: str
    quote: str
    source: SourceDoc
    interpretation: str
    verified: Optional[bool] = None      # filled in by evidence_verifier, not by the LLM

class AgentRole(str, Enum):
    technical = "technical"
    culture = "culture"
    hiring_manager = "hiring_manager"
    skeptic = "skeptic"

class AgentOpinion(BaseModel):
    opinion_id: str
    agent_role: AgentRole
    candidate_id: str
    round: int                           # 0 = independent stage, 1+ = debate rounds
    verdict: Verdict
    confidence: Confidence
    confidence_score: int = Field(default=50, ge=0, le=100, description="Numerical confidence score from 0 to 100")
    confidence_rationale: str
    evidence: list[EvidenceItem]
    open_questions: list[str]
    insufficient_info_flags: list[str]
    revision_of: Optional[str] = None    # opinion_id this revises, if any
    revision_reason: Optional[str] = None

class TensionType(str, Enum):
    contradiction = "contradiction"           # two agents cite conflicting facts
    weighting_conflict = "weighting_conflict"  # same facts, different importance placed on them
    unverified_claim_dispute = "unverified_claim_dispute"

class Tension(BaseModel):
    tension_id: str
    agent_a: AgentRole
    agent_b: AgentRole
    claim_a: str
    claim_b: str
    tension_type: TensionType
    priority_score: float   # 0-1, higher = more load-bearing for the final decision

class ResponseType(str, Enum):
    rebut = "rebut"
    concede = "concede"
    partial_agree = "partial_agree"

class DebateTurn(BaseModel):
    turn_id: str
    round: int
    tension_id: str
    source_agent: AgentRole
    target_agent: AgentRole
    source_claim: str
    source_quote: str
    response_type: ResponseType
    response_evidence: list[EvidenceItem]
    prior_verdict: Verdict = Verdict.insufficient_data
    new_verdict: Optional[Verdict] = None       # None if unchanged
    prior_confidence: Confidence = Confidence.medium
    new_confidence: Optional[Confidence] = None
    prior_confidence_score: int = 50
    new_confidence_score: Optional[int] = None

class WeightClass(str, Enum):
    decisive = "decisive"
    major = "major"
    minor = "minor"
    informational = "informational"

class WeightingRationale(BaseModel):
    dimension: str
    weight_class: WeightClass
    justification: str
    jd_requirement_ref: str     # which line of the JD this ties to

class UnresolvedDisagreement(BaseModel):
    tension_id: str
    description: str
    agents_involved: list[AgentRole]
    why_unresolved: str

class Recommendation(str, Enum):
    strong_hire = "strong_hire"
    hire = "hire"
    hire_with_reservations = "hire_with_reservations"
    no_hire = "no_hire"

class FinalDecision(BaseModel):
    candidate_id: str
    recommendation: Recommendation
    confidence: Confidence
    weighting_rationale: list[WeightingRationale]
    strengths: list[EvidenceItem]
    concerns: list[EvidenceItem]
    unresolved_disagreements: list[UnresolvedDisagreement]

import itertools
import uuid
from thefuzz import fuzz
from src.schemas import AgentOpinion, Tension, TensionType, Verdict, Confidence

MAX_TENSIONS_PER_ROUND = 3
FUZZ_THRESHOLD = 85

def verdict_polarity(verdict: Verdict) -> int:
    if verdict in (Verdict.strong_hire, Verdict.hire, Verdict.lean_hire):
        return 1
    elif verdict in (Verdict.lean_no_hire, Verdict.no_hire):
        return -1
    return 0

def verdict_score(verdict: Verdict) -> float:
    scores = {
        Verdict.strong_hire: 2.0,
        Verdict.hire: 1.0,
        Verdict.lean_hire: 0.5,
        Verdict.insufficient_data: 0.0,
        Verdict.lean_no_hire: -0.5,
        Verdict.no_hire: -1.0,
    }
    return scores.get(verdict, 0.0)

def confidence_score(confidence: Confidence) -> float:
    scores = {
        Confidence.high: 1.0,
        Confidence.medium: 0.5,
        Confidence.low: 0.2
    }
    return scores.get(confidence, 0.0)

def implied_weight(opinion: AgentOpinion) -> float:
    return verdict_score(opinion.verdict) * confidence_score(opinion.confidence)

def shares_subject(evidence_a, evidence_b) -> bool:
    for a in evidence_a:
        for b in evidence_b:
            if fuzz.partial_ratio(a.quote.lower(), b.quote.lower()) > FUZZ_THRESHOLD or \
               fuzz.partial_ratio(a.claim.lower(), b.claim.lower()) > FUZZ_THRESHOLD:
                return True
    return False

def find_shared_cited_fact(evidence_a, evidence_b):
    for a in evidence_a:
        for b in evidence_b:
            if fuzz.partial_ratio(a.quote.lower(), b.quote.lower()) > FUZZ_THRESHOLD:
                return a.quote, a.claim, b.claim
    return None

def undercuts(flags: list[str], evidence) -> tuple:
    for flag in flags:
        for ev in evidence:
            if fuzz.partial_ratio(flag.lower(), ev.claim.lower()) > FUZZ_THRESHOLD or \
               fuzz.partial_ratio(flag.lower(), ev.quote.lower()) > FUZZ_THRESHOLD:
                return flag, ev.claim
    return None

def make_tension(a: AgentOpinion, b: AgentOpinion, t_type: TensionType, claim_a: str, claim_b: str) -> Tension:
    # Priority score: base score + confidence spread + absolute weight spread
    conf_spread = abs(confidence_score(a.confidence) - confidence_score(b.confidence))
    weight_spread = abs(implied_weight(a) - implied_weight(b))
    
    priority_score = (conf_spread + weight_spread) / 4.0 # normalize somewhat
    if t_type == TensionType.contradiction:
        priority_score += 0.5
    
    return Tension(
        tension_id=str(uuid.uuid4()),
        agent_a=a.agent_role,
        agent_b=b.agent_role,
        claim_a=claim_a,
        claim_b=claim_b,
        tension_type=t_type,
        priority_score=min(1.0, priority_score)
    )

def detect_tensions(opinions: list[AgentOpinion]) -> list[Tension]:
    tensions = []
    
    for a, b in itertools.combinations(opinions, 2):
        # 1. Contradiction
        if verdict_polarity(a.verdict) != verdict_polarity(b.verdict) and shares_subject(a.evidence, b.evidence):
            # Find the overlapping claims
            c_a, c_b = "General opposing evidence", "General opposing evidence"
            for ev_a in a.evidence:
                for ev_b in b.evidence:
                    if fuzz.partial_ratio(ev_a.quote.lower(), ev_b.quote.lower()) > FUZZ_THRESHOLD or \
                       fuzz.partial_ratio(ev_a.claim.lower(), ev_b.claim.lower()) > FUZZ_THRESHOLD:
                        c_a, c_b = ev_a.claim, ev_b.claim
                        break
            
            tensions.append(make_tension(a, b, TensionType.contradiction, c_a, c_b))

        # 2. Weighting conflict
        shared = find_shared_cited_fact(a.evidence, b.evidence)
        if shared:
            quote, c_a, c_b = shared
            weight_diff = abs(implied_weight(a) - implied_weight(b))
            if weight_diff > 0.5 and verdict_polarity(a.verdict) == verdict_polarity(b.verdict): 
                # Avoid double counting if it's already a contradiction
                tensions.append(make_tension(a, b, TensionType.weighting_conflict, c_a, c_b))

        # 3. Unverified claim dispute
        undercut_a_on_b = undercuts(a.insufficient_info_flags, b.evidence)
        if undercut_a_on_b:
            flag, claim = undercut_a_on_b
            tensions.append(make_tension(a, b, TensionType.unverified_claim_dispute, flag, claim))
            
        undercut_b_on_a = undercuts(b.insufficient_info_flags, a.evidence)
        if undercut_b_on_a:
            flag, claim = undercut_b_on_a
            tensions.append(make_tension(b, a, TensionType.unverified_claim_dispute, flag, claim))

    # Sort and return top MAX_TENSIONS_PER_ROUND
    tensions.sort(key=lambda t: t.priority_score, reverse=True)
    return tensions[:MAX_TENSIONS_PER_ROUND]

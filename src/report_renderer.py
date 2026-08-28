from src.schemas import FinalDecision, CandidateProfile, AgentOpinion, DebateTurn

def render_final_report(decision: FinalDecision, profile: CandidateProfile, opinions_dict: dict, debate_log: list[DebateTurn]) -> str:
    lines = []
    lines.append(f"# Candidate Report — {profile.name} ({profile.candidate_id})")
    lines.append("")
    lines.append(f"## Recommendation: {decision.recommendation.value}  (confidence: {decision.confidence.value})")
    lines.append("")
    
    lines.append("## Strengths")
    for item in decision.strengths:
        lines.append(f"- {item.claim} — \"{item.quote}\" ({item.source.value})")
    lines.append("")
    
    lines.append("## Concerns")
    for item in decision.concerns:
        lines.append(f"- {item.claim} — \"{item.quote}\" ({item.source.value})")
    lines.append("")
    
    lines.append("## How this decision was weighted")
    for weight in decision.weighting_rationale:
        lines.append(f"- **{weight.dimension}** [{weight.weight_class.value}]: {weight.justification} (JD ref: {weight.jd_requirement_ref})")
    lines.append("")
    
    lines.append("## Unresolved disagreements")
    if not decision.unresolved_disagreements:
        lines.append("- None — all raised tensions were resolved during debate.")
    else:
        for dis in decision.unresolved_disagreements:
            agents = ", ".join([a.value for a in dis.agents_involved])
            lines.append(f"- Between {agents}: {dis.description} — not resolved because {dis.why_unresolved}")
    lines.append("")
    
    lines.append("## Full audit trail")
    lines.append(f"- Candidate profile: runs/{profile.candidate_id}_profile.json")
    lines.append(f"- Final opinions (4): runs/{profile.candidate_id}_opinions.json")
    lines.append(f"- Debate log ({len(debate_log)} turns): runs/{profile.candidate_id}_debate_log.json")
    lines.append(f"- This decision: runs/{profile.candidate_id}_decision.json")
    
    return "\n".join(lines)

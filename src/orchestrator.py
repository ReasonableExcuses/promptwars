import os
import json
import time
import traceback
from src.schemas import AgentRole
from src.profile_builder import build_profile
from src.agents.runner import call_agent
from src.evidence_verifier import verify_evidence, verify_evidence_on_turn
from src.tension_detector import detect_tensions
from src.debate_engine import run_debate_turn, apply_revision
from src.decision_synthesizer import call_decision_synthesizer
from src.report_renderer import render_final_report

MAX_ROUNDS = 2

def sanitize_unverified_evidence(opinion):
    """Moves unverified evidence to insufficient_info_flags"""
    valid_evidence = []
    for ev in opinion.evidence:
        if ev.verified:
            valid_evidence.append(ev)
        else:
            opinion.insufficient_info_flags.append(f"Unverified claim: {ev.claim}")
    opinion.evidence = valid_evidence
    return opinion

def run_pipeline(candidate_id: str, name: str, resume_text: str, transcript_text: str, jd_text: str, progress_callback=None) -> str:
    def log(msg):
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    log(f"[{candidate_id}] Building profile...")
    profile = build_profile(resume_text, transcript_text, "AI Engineer — Agentic Systems (Freight Operations)")
    profile.candidate_id = candidate_id
    profile.name = name

    # Persist profile
    os.makedirs("runs", exist_ok=True)
    with open(f"runs/{candidate_id}_profile.json", "w") as f:
        f.write(profile.model_dump_json(indent=2))

    log(f"[{candidate_id}] Collecting independent opinions...")
    opinions = {}
    for role in [AgentRole.technical, AgentRole.culture, AgentRole.hiring_manager, AgentRole.skeptic]:
        log(f"  -> Calling {role.value} agent...")
        time.sleep(5)
        raw_opinion = call_agent(role, profile, resume_text, transcript_text, jd_text)
        raw_opinion.candidate_id = candidate_id
        
        verified_opinion = verify_evidence(raw_opinion, resume_text + transcript_text)
        opinions[role] = sanitize_unverified_evidence(verified_opinion)

    # Persist round 0 opinions
    with open(f"runs/{candidate_id}_opinions_round0.json", "w") as f:
        json.dump({k.value: v.model_dump() for k, v in opinions.items()}, f, indent=2)

    debate_log = []
    tensions = []
    log(f"[{candidate_id}] Entering debate stage...")
    for round_num in range(1, MAX_ROUNDS + 1):
        log(f"  -> Round {round_num}")
        tensions = detect_tensions(list(opinions.values()))
        if not tensions:
            log("  -> No tensions detected. Converged.")
            break
        
        any_revision = False
        for tension in tensions:
            log(f"    -> Tension detected between {tension.agent_a.value} and {tension.agent_b.value}: {tension.tension_type.value}")
            time.sleep(5)
            
            # Agent B responds to Agent A
            turn_b = run_debate_turn(tension, opinions, round_num, target_agent=tension.agent_b, source_agent=tension.agent_a)
            turn_b = verify_evidence_on_turn(turn_b, resume_text + transcript_text)
            turn_b.response_evidence = [ev for ev in turn_b.response_evidence if ev.verified]
            debate_log.append(turn_b)
            
            if turn_b.new_verdict or turn_b.new_confidence:
                log(f"      -> {turn_b.target_agent.value} revised opinion ({turn_b.response_type.value})")
                opinions[turn_b.target_agent] = apply_revision(opinions[turn_b.target_agent], turn_b)
                any_revision = True
            else:
                log(f"      -> {turn_b.target_agent.value} stood firm ({turn_b.response_type.value})")
                
            time.sleep(5)
            
            # Agent A responds to Agent B
            turn_a = run_debate_turn(tension, opinions, round_num, target_agent=tension.agent_a, source_agent=tension.agent_b)
            turn_a = verify_evidence_on_turn(turn_a, resume_text + transcript_text)
            turn_a.response_evidence = [ev for ev in turn_a.response_evidence if ev.verified]
            debate_log.append(turn_a)
            
            if turn_a.new_verdict or turn_a.new_confidence:
                log(f"      -> {turn_a.target_agent.value} revised opinion ({turn_a.response_type.value})")
                opinions[turn_a.target_agent] = apply_revision(opinions[turn_a.target_agent], turn_a)
                any_revision = True
            else:
                log(f"      -> {turn_a.target_agent.value} stood firm ({turn_a.response_type.value})")
                
        if not any_revision:
            log("  -> No revisions made. Converged.")
            break

    # Re-evaluate tensions after final round to capture unresolved ones
    tensions = detect_tensions(list(opinions.values()))

    # Persist final opinions and debate log
    with open(f"runs/{candidate_id}_opinions.json", "w") as f:
        json.dump({k.value: v.model_dump() for k, v in opinions.items()}, f, indent=2)
    with open(f"runs/{candidate_id}_debate_log.json", "w") as f:
        json.dump([t.model_dump() for t in debate_log], f, indent=2)

    log(f"[{candidate_id}] Synthesizing final decision...")
    time.sleep(5)
    try:
        decision = call_decision_synthesizer(jd_text, opinions, debate_log, tensions)
    except Exception as e:
        log(f"Error during decision synthesis: {e}")
        traceback.print_exc()
        return "Failed to synthesize decision."
        
    with open(f"runs/{candidate_id}_decision.json", "w") as f:
        f.write(decision.model_dump_json(indent=2))

    report = render_final_report(decision, profile, opinions, debate_log)
    
    with open(f"runs/{candidate_id}_final_report.md", "w") as f:
        f.write(report)
        
    log(f"[{candidate_id}] Done.")
    return report

def run_all_candidates(candidates: list[dict]) -> list[str]:
    return [run_pipeline(**c) for c in candidates]

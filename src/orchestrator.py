import os
import json
import traceback
import re
import concurrent.futures
from typing import Callable, Optional, Dict, List
from src.schemas import AgentRole
from src.profile_builder import build_profile
from src.agents.runner import call_agent
from src.evidence_verifier import verify_evidence, verify_evidence_on_turn
from src.tension_detector import detect_tensions
from src.debate_engine import run_debate_turn, apply_revision
from src.decision_synthesizer import call_decision_synthesizer
from src.report_renderer import render_final_report

MAX_ROUNDS = 2

def sanitize_filename(cid: str) -> str:
    """Sanitizes candidate ID to prevent path traversal (LFI)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', cid) or "unknown_candidate"

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

def run_pipeline(candidate_id: str, name: str, resume_text: str, transcript_text: str, jd_text: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
    candidate_id = sanitize_filename(candidate_id)
    
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    log(f"🛠️ **Phase 1:** Extracting Profile for `{candidate_id}` from source documents...")
    profile = build_profile(resume_text, transcript_text, "AI Engineer — Agentic Systems (Freight Operations)")
    profile.candidate_id = candidate_id
    profile.name = name

    # Persist profile
    os.makedirs("runs", exist_ok=True)
    with open(f"runs/{candidate_id}_profile.json", "w", encoding="utf-8") as f:
        f.write(profile.model_dump_json(indent=2))

    log(f"🤖 **Phase 2:** Collecting Independent Opinions (Parallelizing Requests)...")
    opinions = {}
    
    def fetch_opinion(role: AgentRole):
        log(f"  ↳ Booting `{role.value.upper()}` agent...")
        raw_opinion = call_agent(role, profile, resume_text, transcript_text, jd_text)
        raw_opinion.candidate_id = candidate_id
        verified_opinion = verify_evidence(raw_opinion, resume_text + transcript_text)
        return role, sanitize_unverified_evidence(verified_opinion)
        
    roles = [AgentRole.technical, AgentRole.culture, AgentRole.hiring_manager, AgentRole.skeptic]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_opinion, r): r for r in roles}
        for future in concurrent.futures.as_completed(futures):
            role, opinion = future.result()
            opinions[role] = opinion

    # Persist round 0 opinions
    with open(f"runs/{candidate_id}_opinions_round0.json", "w", encoding="utf-8") as f:
        json.dump({k.value: v.model_dump() for k, v in opinions.items()}, f, indent=2)

    debate_log = []
    tensions = []
    log(f"⚔️ **Phase 3:** Entering Debate & Cross-Examination...")
    for round_num in range(1, MAX_ROUNDS + 1):
        log(f"🔄 **Debate Round {round_num}**")
        tensions = detect_tensions(list(opinions.values()))
        if not tensions:
            log("🤝 **Consensus:** No tensions detected. Agents are aligned.")
            break
        
        any_revision = False
        for tension in tensions:
            a_conf = opinions[tension.agent_a].confidence_score
            b_conf = opinions[tension.agent_b].confidence_score
            gap = abs(a_conf - b_conf)
            log(f"⚡ **TENSION DETECTED:** {tension.agent_a.value.upper()} vs {tension.agent_b.value.upper()}")
            log(f"  ↳ Type: {tension.tension_type.value} | Disagreement Magnitude: **{gap} points**")
            
            # Agent B responds to Agent A
            turn_b = run_debate_turn(tension, opinions, round_num, target_agent=tension.agent_b, source_agent=tension.agent_a)
            turn_b = verify_evidence_on_turn(turn_b, resume_text + transcript_text)
            turn_b.response_evidence = [ev for ev in turn_b.response_evidence if ev.verified]
            debate_log.append(turn_b)
            
            if turn_b.new_verdict or turn_b.new_confidence or turn_b.new_confidence_score:
                log(f"  ↳ {turn_b.target_agent.value.upper()} **{turn_b.response_type.value.upper()}** (Revised opinion)")
                opinions[turn_b.target_agent] = apply_revision(opinions[turn_b.target_agent], turn_b)
                any_revision = True
            else:
                log(f"  ↳ {turn_b.target_agent.value.upper()} **{turn_b.response_type.value.upper()}** (Stood firm)")
            
            # Agent A responds to Agent B
            turn_a = run_debate_turn(tension, opinions, round_num, target_agent=tension.agent_a, source_agent=tension.agent_b)
            turn_a = verify_evidence_on_turn(turn_a, resume_text + transcript_text)
            turn_a.response_evidence = [ev for ev in turn_a.response_evidence if ev.verified]
            debate_log.append(turn_a)
            
            if turn_a.new_verdict or turn_a.new_confidence or turn_a.new_confidence_score:
                log(f"  ↳ {turn_a.target_agent.value.upper()} **{turn_a.response_type.value.upper()}** (Revised opinion)")
                opinions[turn_a.target_agent] = apply_revision(opinions[turn_a.target_agent], turn_a)
                any_revision = True
            else:
                log(f"  ↳ {turn_a.target_agent.value.upper()} **{turn_a.response_type.value.upper()}** (Stood firm)")
                
        if not any_revision:
            log("🤝 **Debate Concluded:** Agents reached convergence with no further revisions.")
            break
    else:
        log("⚠️ **Debate Exhausted:** Maximum rounds reached. Unresolved tensions escalated to Chair.")

    # Re-evaluate tensions after final round to capture unresolved ones
    tensions = detect_tensions(list(opinions.values()))

    # Persist final opinions and debate log
    with open(f"runs/{candidate_id}_opinions.json", "w", encoding="utf-8") as f:
        json.dump({k.value: v.model_dump() for k, v in opinions.items()}, f, indent=2)
    with open(f"runs/{candidate_id}_debate_log.json", "w", encoding="utf-8") as f:
        json.dump([t.model_dump() for t in debate_log], f, indent=2)

    log(f"⚖️ **Phase 4:** Synthesizing Final Decision (Chair Agent)...")
    try:
        decision = call_decision_synthesizer(jd_text, opinions, debate_log, tensions)
    except Exception as e:
        log(f"Error during decision synthesis: {e}")
        traceback.print_exc()
        return "Failed to synthesize decision."
        
    with open(f"runs/{candidate_id}_decision.json", "w", encoding="utf-8") as f:
        f.write(decision.model_dump_json(indent=2))

    report = render_final_report(decision, profile, opinions, debate_log)
    
    with open(f"runs/{candidate_id}_final_report.md", "w", encoding="utf-8") as f:
        f.write(report)
        
    log(f"[{candidate_id}] Done.")
    return report

def run_all_candidates(candidates: list[dict]) -> list[str]:
    return [run_pipeline(**c) for c in candidates]

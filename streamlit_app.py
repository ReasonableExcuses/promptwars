import streamlit as st
import json
import os
import re
from typing import Optional, Dict, List, Union

# Create a minimal wrapper if running pipeline
try:
    from src.orchestrator import run_pipeline
except ImportError:
    run_pipeline = None

st.set_page_config(page_title="PromptWars Evaluator", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS FOR PREMIUM UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.5rem;
        margin-bottom: 0px;
        padding-bottom: 10px;
    }
    
    .subtitle {
        color: #a0aec0;
        font-size: 1.2rem;
        margin-bottom: 30px;
    }
    
    /* Glassmorphism Metric Cards (Native Streamlit Hack) */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 25px rgba(78, 205, 196, 0.15);
    }
    
    /* Custom Verdict Pills */
    .verdict-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-top: 10px;
    }
    .strong_hire { background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 1px solid #4ade80; }
    .hire { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; }
    .lean_hire { background: rgba(129, 140, 248, 0.15); color: #818cf8; border: 1px solid #818cf8; }
    .lean_no_hire { background: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1px solid #fbbf24; }
    .no_hire { background: rgba(248, 113, 113, 0.15); color: #f87171; border: 1px solid #f87171; }
    .insufficient_data { background: rgba(156, 163, 175, 0.15); color: #9ca3af; border: 1px solid #9ca3af; }
    
    /* Timeline styling */
    .timeline-container {
        border-left: 3px solid rgba(78, 205, 196, 0.3);
        padding-left: 25px;
        margin-left: 15px;
        margin-top: 20px;
    }
    .timeline-node {
        position: relative;
        margin-bottom: 25px;
        padding: 20px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: transform 0.2s;
    }
    .timeline-node:hover {
        transform: translateX(8px);
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(78, 205, 196, 0.3);
    }
    .timeline-node::before {
        content: '';
        position: absolute;
        left: -33px;
        top: 24px;
        width: 14px;
        height: 14px;
        background-color: #FF6B6B;
        border-radius: 50%;
        box-shadow: 0 0 10px rgba(255, 107, 107, 0.6);
    }
    
    .agent-name {
        font-weight: 800;
        color: #e2e8f0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<header><h1 class="main-title" aria-label="Main Application Title">Multi-Agent AI Interview Panel</h1></header>', unsafe_allow_html=True)
st.markdown('<div class="subtitle" role="doc-subtitle">Simulating real-world debate among distinct AI personas with cross-examination.</div>', unsafe_allow_html=True)

# Sidebar
st.sidebar.image("https://via.placeholder.com/400x150.png?text=PromptWars+Engine", use_container_width=True)
st.sidebar.header("⚙️ Configuration")

api_key = st.sidebar.text_input("Groq API Key", type="password")
if api_key:
    os.environ["GROQ_API_KEY"] = api_key

candidate_options = {
    "Candidate A": "Candidate_A", 
    "Candidate B": "Candidate_B",
    "✨ Custom Input": "Custom_Candidate"
}
selected_candidate_name = st.sidebar.selectbox("Select Candidate", list(candidate_options.keys()))

def sanitize_filename(cid: str) -> str:
    """Sanitizes candidate ID to prevent path traversal (LFI)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', cid) or "unknown_candidate"

cid = sanitize_filename(candidate_options[selected_candidate_name])

# Helpers
@st.cache_data
def load_json(filepath: str) -> Union[Dict, List, None]:
    """Securely loads JSON from disk with caching for performance."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

@st.cache_data
def load_file(filepath: str) -> Optional[str]:
    """Securely loads raw text files from disk with caching."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return None

def run_live_pipeline(cid_key: str, custom_resume: Optional[str] = None, custom_transcript: Optional[str] = None, custom_jd: Optional[str] = None) -> None:
    if not os.environ.get("GROQ_API_KEY"):
        st.sidebar.error("Please provide a Groq API Key.")
        return
        
    with st.status(f"🚀 Running orchestration pipeline for {cid_key}...", expanded=True) as status:
        resume = custom_resume or load_file(f"data/{cid_key.lower()}_resume.txt")
        transcript = custom_transcript or load_file(f"data/{cid_key.lower()}_transcript.txt")
        jd = custom_jd or load_file(f"data/job_description.txt")
        
        def progress_callback(msg):
            st.write(msg)
            
        try:
            report = run_pipeline(
                candidate_id=cid_key,
                name=cid_key.replace("_", " "),
                resume_text=resume or "",
                transcript_text=transcript or "",
                jd_text=jd or "",
                progress_callback=progress_callback
            )
            status.update(label="✨ Pipeline Complete!", state="complete", expanded=False)
        except Exception as e:
            status.update(label=f"❌ Pipeline Failed: {e}", state="error")
            st.error(str(e))

custom_jd, custom_resume, custom_transcript = None, None, None
if cid == "Custom_Candidate":
    st.markdown("### 📝 Custom Input Data")
    st.info("💡 Paste your custom text below, then click **▶️ Run End-to-End Pipeline** in the sidebar to test the engine on your own data.")
    custom_jd = st.text_area("Job Description", placeholder="Paste Job Description here...", height=200)
    custom_resume = st.text_area("Candidate Resume", placeholder="Paste Resume here...", height=200)
    custom_transcript = st.text_area("Interview Transcript", placeholder="Paste Interview Transcript here...", height=200)
    st.divider()

if st.sidebar.button("▶️ Run End-to-End Pipeline", type="primary", use_container_width=True):
    if cid == "Custom_Candidate" and not (custom_jd and custom_resume and custom_transcript):
        st.sidebar.error("Please fill all custom input fields!")
    else:
        run_live_pipeline(cid, custom_resume, custom_transcript, custom_jd)

# Load Data
data_dir = "runs"
profile = load_json(f"{data_dir}/{cid}_profile.json")
opinions_round0 = load_json(f"{data_dir}/{cid}_opinions_round0.json")
debate_log = load_json(f"{data_dir}/{cid}_debate_log.json")
decision = load_json(f"{data_dir}/{cid}_decision.json")
final_report = load_file(f"{data_dir}/{cid}_final_report.md")

if not profile or not opinions_round0:
    st.info(f"⏳ **Awaiting Execution:** No data found for `{cid}` in the `{data_dir}/` directory. Please click **▶️ Run End-to-End Pipeline** in the sidebar to generate the evaluation.")
    st.stop()

# Layout Tabs
tabs = st.tabs(["📊 Independent Opinions", "🔥 Debate Timeline", "📝 Final Report", "⚖️ Compare Candidates"])

# TAB 1: Independent Opinions
with tabs[0]:
    st.markdown("### Initial Independent Opinions (Round 0)")
    st.markdown("Before cross-examination, each persona evaluates the candidate independently based purely on their instructions.")
    
    cols = st.columns(4)
    agents = [
        ("technical", "💻"), 
        ("culture", "🌱"), 
        ("hiring_manager", "👔"), 
        ("skeptic", "🕵️")
    ]
    
    for idx, (agent_key, icon) in enumerate(agents):
        with cols[idx]:
            if agent_key in opinions_round0:
                op = opinions_round0[agent_key]
                verdict = op.get('verdict', 'unknown')
                conf = op.get('confidence', 'unknown')
                score = op.get('confidence_score', 50)
                
                # Render using native metric which we styled via CSS
                st.metric(label=f"{icon} {agent_key.replace('_', ' ').title()}", value=f"{conf.upper()} ({score}/100)", delta=verdict.upper().replace("_", " "), delta_color="off")
                
                # Use raw HTML for the beautiful pill styling underneath
                st.markdown(f'<div class="verdict-pill {verdict}" role="status" aria-label="Verdict: {verdict}">{verdict.replace("_", " ")}</div>', unsafe_allow_html=True)
                
                with st.expander("View Evidence (Verification Check)", expanded=True):
                    for ev in op.get('evidence', [])[:3]:
                        if ev.get("verified"):
                            st.markdown(f'<article aria-label="Verified Source Evidence" style="border-left: 4px solid #4ade80; padding-left: 12px; margin-bottom: 12px; font-size: 0.95rem;">✅ <strong>VERIFIED SOURCE:</strong><br/><em>"{ev.get("quote")}"</em><br/><span style="color:#a0aec0; font-size: 0.85rem;">Interpretation: {ev.get("interpretation")}</span></article>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<article aria-label="Hallucinated Evidence Error" role="alert" style="border-left: 4px solid #f87171; padding: 12px; margin-bottom: 12px; background: rgba(248,113,113,0.1); border-radius: 4px; font-size: 0.95rem;">❌ <strong>HALLUCINATION DETECTED</strong><br/><span style="color:#f87171;">Agent hallucinates quote not present in source text:</span><br/><em>"{ev.get("quote")}"</em></article>', unsafe_allow_html=True)
            else:
                st.info(f"{icon} No data.")

# TAB 2: Debate Timeline
with tabs[1]:
    st.markdown("### Cross-Examination & Debate")
    st.markdown("The Orchestrator detects tensions between independent opinions and forces the agents to debate and defend their claims.")
    
    if debate_log is None:
        st.warning("⚠️ **The debate log is missing.** This usually means the pipeline crashed halfway through (often due to Groq API rate limits) before it could finish the cross-examination phase. Please click 'Run End-to-End Pipeline' again.")
    elif len(debate_log) == 0:
        st.success("No debates occurred. The agents converged immediately!")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("#### 🗣️ Voice Debate Session")
            st.markdown("Listen to the AI personas argue their points using distinct regional accents (powered by gTTS).")
            if st.button("Generate & Play Audio", type="primary", key=f"audio_{cid}"):
                try:
                    from src.voice_synthesizer import generate_debate_audio
                    with st.spinner("Generating distinct voices for AI personas..."):
                        audio_path = os.path.join(data_dir, f"{cid}_debate.mp3")
                        generate_debate_audio(debate_log, audio_path)
                        st.audio(audio_path, format="audio/mp3")
                except ImportError:
                    st.error("gTTS is not installed or voice synthesizer module is missing.")
                except Exception as e:
                    st.error(f"Voice synthesis failed: {e}")
        st.divider()
        
        # Create HTML timeline
        timeline_html = '<section class="timeline-container" aria-label="Debate Timeline">'
        
        for turn in debate_log:
            rd = turn.get('round', 1)
            src = turn.get('source_agent', 'Unknown')
            tgt = turn.get('target_agent', 'Unknown')
            claim = turn.get('source_claim', '')
            resp = turn.get('response_type', 'unknown')
            prior_v = turn.get('prior_verdict', 'unknown').upper()
            new_v = turn.get('new_verdict', 'unknown')
            
            color = "#4ade80" if resp == "concede" else "#f87171" if resp == "rebut" else "#fbbf24"
            resp_span = f'<span style="color: {color}; font-weight: bold; text-transform: uppercase;">{resp}</span>'
            
            verdict_shift = ""
            if new_v and new_v != turn.get('prior_verdict'):
                verdict_shift = f'<div style="margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 5px;" role="status" aria-label="Verdict Shift"><strong>Verdict Shift:</strong> <s>{prior_v}</s> ➡️ <span style="color: #4ECDC4;">{new_v.upper()}</span></div>'
            
            node_html = f"""
            <article class="timeline-node" aria-label="Debate Turn">
                <div style="font-size: 0.8rem; color: #a0aec0; margin-bottom: 5px;">ROUND {rd} TENSION</div>
                <div><span class="agent-name">{src}</span> claimed: <em>"{claim}"</em></div>
                <div style="margin-top: 10px;"><span class="agent-name">{tgt}</span> responded: {resp_span}</div>
                {verdict_shift}
            </article>
            """
            timeline_html += node_html
            
        timeline_html += '</section>'
        st.markdown(timeline_html, unsafe_allow_html=True)

# TAB 3: Final Report
with tabs[2]:
    if final_report:
        st.markdown(final_report)
    else:
        st.warning("⚠️ **Final report missing.** The pipeline likely crashed (due to API rate limits or errors) before it could synthesize the final decision. Please click 'Run End-to-End Pipeline' again.")

# TAB 4: Compare Candidates
with tabs[3]:
    st.markdown("### Executive Summary")
    comp_cols = st.columns(len(candidate_options))
    valid_decisions = {}
    
    for idx, (name, key) in enumerate(candidate_options.items()):
        with comp_cols[idx]:
            st.subheader(name)
            dec = load_json(f"{data_dir}/{key}_decision.json")
            if dec:
                valid_decisions[name] = dec
                rec = dec.get('recommendation', 'unknown')
                
                # Pill for final decision
                st.markdown(f'<div class="verdict-pill {rec}" role="status" aria-label="Final Recommendation: {rec}">{rec.upper()}</div>', unsafe_allow_html=True)
                st.write("")
                
                with st.expander("Key Strengths", expanded=True):
                    for ev in dec.get('strengths', []):
                        st.markdown(f"- {ev.get('claim')}")
                        
                with st.expander("Major Concerns", expanded=True):
                    for ev in dec.get('concerns', []):
                        st.markdown(f"- {ev.get('claim')}")
            else:
                st.write("No decision available.")

    st.divider()
    st.markdown("### ⚖️ VP of Engineering - Comparative Ranking")
    if len(valid_decisions) >= 2:
        if st.button("▶️ Run Comparative Analysis", type="primary", use_container_width=True):
            try:
                from src.agents.runner import call_comparator
            except ImportError:
                st.error("Could not import runner. Ensure you are running locally or the backend is configured.")
            else:
                jd = load_file("data/job_description.txt")
                if jd:
                    with st.spinner("VP of Engineering is analyzing the trade-offs..."):
                        try:
                            comp_report = call_comparator(jd, valid_decisions)
                            
                            winner = comp_report.recommended_winner
                            st.success(f"**Recommended Winner:** {winner if winner else 'Tie / Depends on Priorities'}")
                            
                            st.markdown("#### Tradeoff Summary")
                            st.info(comp_report.tradeoff_summary)
                            
                            st.markdown("#### Candidate Advantages")
                            for c_name, adv in comp_report.candidate_advantages.items():
                                st.markdown(f"- **{c_name}:** {adv}")
                        except Exception as e:
                            st.error(f"Comparator Error: {e}")
                else:
                    st.error("Could not load Job Description.")
    else:
        st.info("Run the pipeline for at least two candidates to unlock Comparative Ranking.")

import streamlit as st
import json
import os
import time

# Create a minimal wrapper if running pipeline
try:
    from src.orchestrator import run_pipeline
except ImportError:
    run_pipeline = None

st.set_page_config(page_title="Multi-Agent AI Interview Panel", layout="wide")

st.title("🤖 Multi-Agent Evaluator Panel")

# Sidebar
st.sidebar.header("Configuration")
mode = st.sidebar.radio("Run Mode", ["View Example (Offline)", "Live Run (Requires API Key)"])

if mode == "Live Run (Requires API Key)":
    api_key = st.sidebar.text_input("Groq API Key", type="password")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key

candidate_options = {"Candidate A": "Candidate_A", "Candidate B": "Candidate_B"}
selected_candidate_name = st.sidebar.selectbox("Select Candidate", list(candidate_options.keys()))
cid = candidate_options[selected_candidate_name]

# Helper to load JSON
def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return None

def load_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return f.read()
    return None

def run_live_pipeline(cid_key):
    if not os.environ.get("GROQ_API_KEY"):
        st.error("Please provide a Groq API Key in the sidebar.")
        return
        
    with st.status(f"Running pipeline for {cid_key}...", expanded=True) as status:
        # Load raw texts
        resume = load_file(f"data/{cid_key.lower()}_resume.txt")
        transcript = load_file(f"data/{cid_key.lower()}_transcript.txt")
        jd = load_file(f"data/job_description.txt")
        
        # We define a progress callback that updates the status box
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
            status.update(label="Pipeline Complete!", state="complete", expanded=False)
        except Exception as e:
            status.update(label=f"Pipeline Failed: {e}", state="error")
            st.error(str(e))

if mode == "Live Run (Requires API Key)":
    if st.sidebar.button("Run Pipeline", type="primary"):
        run_live_pipeline(cid)

# Data Loading (either from runs/ if live, or examples/ if example mode)
data_dir = "examples" if mode == "View Example (Offline)" else "runs"

profile = load_json(f"{data_dir}/{cid}_profile.json")
opinions_round0 = load_json(f"{data_dir}/{cid}_opinions_round0.json")
debate_log = load_json(f"{data_dir}/{cid}_debate_log.json")
decision = load_json(f"{data_dir}/{cid}_decision.json")
final_report = load_file(f"{data_dir}/{cid}_final_report.md")

if not profile or not opinions_round0:
    st.info(f"No data found for {cid} in `{data_dir}/`. Please run the pipeline or ensure examples exist.")
    st.stop()

# Layout Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Independent Opinions (Round 0)", "Debate Timeline", "Final Report", "Compare Candidates"])

# TAB 1: Independent Opinions
with tab1:
    st.header(f"Initial Independent Opinions ({selected_candidate_name})")
    cols = st.columns(4)
    agents = ["technical", "culture", "hiring_manager", "skeptic"]
    
    for idx, agent in enumerate(agents):
        with cols[idx]:
            st.subheader(f"🤖 {agent.replace('_', ' ').title()}")
            if agent in opinions_round0:
                op = opinions_round0[agent]
                
                verdict_colors = {
                    "strong_hire": "green", "hire": "green", "lean_hire": "blue",
                    "lean_no_hire": "orange", "no_hire": "red", "insufficient_data": "gray"
                }
                color = verdict_colors.get(op.get('verdict'), 'gray')
                
                st.markdown(f"**Verdict:** :{color}[**{op.get('verdict').upper()}**]")
                st.markdown(f"**Confidence:** {op.get('confidence').upper()}")
                
                st.write("**Key Evidence:**")
                for ev in op.get('evidence', [])[:3]:  # Show top 3
                    verified = "✅" if ev.get("verified") else "⚠️"
                    st.markdown(f"> \"{ev.get('quote')}\" {verified}")
                    
            else:
                st.write("No opinion recorded.")

# TAB 2: Debate Timeline
with tab2:
    st.header("Debate Timeline")
    if not debate_log:
        st.write("No debates occurred (opinions converged immediately).")
    else:
        for turn in debate_log:
            with st.container():
                st.markdown(f"### Round {turn.get('round')} Tension")
                st.info(f"**{turn.get('source_agent')}** claimed: *\"{turn.get('source_claim')}\"*")
                
                resp = turn.get('response_type')
                color = "green" if resp == "concede" else "red" if resp == "rebut" else "orange"
                st.markdown(f"**{turn.get('target_agent')}** responded: :{color}[**{resp.upper()}**]")
                
                if turn.get('new_verdict'):
                    st.markdown(f"Verdict changed: {turn.get('prior_verdict')} ➡️ **{turn.get('new_verdict')}**")
                else:
                    st.markdown("Verdict remained unchanged.")
                st.divider()

# TAB 3: Final Report
with tab3:
    if final_report:
        st.markdown(final_report)
    else:
        st.write("Final report not available.")

# TAB 4: Compare Candidates
with tab4:
    st.header("Side-by-Side Comparison")
    
    comp_cols = st.columns(2)
    for idx, (name, key) in enumerate(candidate_options.items()):
        with comp_cols[idx]:
            st.subheader(name)
            dec = load_json(f"{data_dir}/{key}_decision.json")
            if dec:
                rec = dec.get('recommendation')
                st.markdown(f"### Final Decision: **{rec.upper()}**")
                
                st.write("**Strengths:**")
                for ev in dec.get('strengths', []):
                    st.markdown(f"- {ev.get('claim')}")
                    
                st.write("**Concerns:**")
                for ev in dec.get('concerns', []):
                    st.markdown(f"- {ev.get('claim')}")
            else:
                st.write("No final decision available.")

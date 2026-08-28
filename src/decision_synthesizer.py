import os
import instructor
from groq import Groq
from src.schemas import FinalDecision, AgentOpinion, DebateTurn, Tension

SYNTHESIZER_SYSTEM_PROMPT = """You are the panel chair. You do not vote and you do not average scores. Your job
is to weigh the panel's evidence and reach a reasoned recommendation, the way a
thoughtful hiring manager would after sitting through the whole debate — not by
computing a mean of four numbers.

You must:
1. Read the job description and identify which of its stated requirements are
   load-bearing for this specific decision (e.g. if the JD states something is a
   "day one" responsibility, a gap there should be weighted more heavily than a
   "nice to have").
2. For each major point of evidence, assign it a weight_class (decisive, major,
   minor, informational) and justify that weight by reference to a specific line
   or theme in the job description — not just "this seems important."
3. Use the FINAL, post-debate opinions and the debate log itself, not the agents'
   original round-0 opinions. If an agent revised its view during debate, that
   revision is what happened — treat it as the agent's real position and note it.
4. For every tension that was raised but NOT resolved in the debate (agents still
   disagree after 2 rounds), you must carry it into unresolved_disagreements
   rather than silently picking a side. State why you could not or chose not to
   resolve it.
5. Every strength and concern you list must carry its own verbatim quote — you may
   pull these directly from the agents' evidence, but do not introduce new claims
   that no agent actually made and verified.
6. If the evidence genuinely doesn't support a confident call in either direction,
   your confidence should be "low" and you should say so plainly rather than
   forcing a decisive-sounding recommendation.

Output must validate against the FinalDecision schema. Return JSON only."""

def call_decision_synthesizer(jd_text: str, opinions_dict: dict, debate_log: list[DebateTurn], tensions: list[Tension]) -> FinalDecision:
    api_key = os.environ.get("GROQ_API_KEY")
    client = instructor.from_groq(Groq(api_key=api_key), mode=instructor.Mode.JSON)
    
    # We only care about the latest opinions. opinions_dict holds the latest ones.
    opinions_json = []
    for role, op in opinions_dict.items():
        opinions_json.append(op.model_dump_json(indent=2))
        
    debate_json = [t.model_dump_json(indent=2) for t in debate_log]
    unresolved_tensions_json = [t.model_dump_json(indent=2) for t in tensions] # Tensions found in the last round

    user_message = f"""=== JOB DESCRIPTION ===
{jd_text}

=== POST-DEBATE AGENT OPINIONS ===
{"\n---\n".join(opinions_json)}

=== DEBATE LOG ===
{"\n---\n".join(debate_json)}

=== UNRESOLVED TENSIONS (STILL EXIST AFTER DEBATE) ===
{"\n---\n".join(unresolved_tensions_json)}
"""

    import time
    for attempt in range(5):
        try:
            decision: FinalDecision = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_model=FinalDecision,
                temperature=0.0
            )
            # Assuming opinions all share the same candidate_id
            if opinions_dict:
                decision.candidate_id = list(opinions_dict.values())[0].candidate_id
                
            return decision
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                print(f"Rate limit hit in decision synthesizer. Sleeping 15s... ({attempt+1}/5)")
                time.sleep(15)
            else:
                raise e
    raise Exception("Max retries exceeded due to rate limits.")

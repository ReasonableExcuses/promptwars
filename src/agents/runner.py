import os
import json
import instructor
from groq import Groq
from src.schemas import AgentOpinion, AgentRole, CandidateProfile

SHARED_RULES = """
You must ground every claim in your evidence list with a verbatim quote from the
resume or transcript — copy it exactly, do not paraphrase inside the quote field.
If you cannot find a real quote for a claim, do not make the claim.

If you do not have enough information to judge a dimension of this role, add it to
insufficient_info_flags and do NOT invent a confidence level to cover the gap.
Confidence should reflect how much real evidence you have, not how the candidate
performed.

You have not seen and must not reference or assume the opinions of any other
reviewer. Form your judgment from the material given to you alone.

Output must validate against the AgentOpinion schema. Return JSON only.
"""

def load_persona_prompt(role: AgentRole) -> str:
    path = os.path.join(os.path.dirname(__file__), "prompts", f"{role.value}.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def call_agent(role: AgentRole, profile: CandidateProfile, resume_text: str, transcript_text: str, jd_text: str) -> AgentOpinion:
    """
    Issues an isolated LLM call for a specific agent persona.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    client = instructor.from_groq(Groq(api_key=api_key), mode=instructor.Mode.JSON)
    
    persona_prompt = load_persona_prompt(role)
    system_prompt = persona_prompt + "\n\n" + SHARED_RULES

    user_message = f"""=== JOB DESCRIPTION ===
{jd_text}

=== CANDIDATE PROFILE ===
{profile.model_dump_json(indent=2)}

=== RESUME ===
{resume_text}

=== TRANSCRIPT ===
{transcript_text}
"""

    import time
    for attempt in range(5):
        try:
            opinion: AgentOpinion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_model=AgentOpinion,
                temperature=0.0
            )
            return opinion
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                print(f"Rate limit hit in runner. Sleeping 15s... ({attempt+1}/5)")
                time.sleep(15)
            else:
                raise e
    raise Exception("Max retries exceeded due to rate limits.")

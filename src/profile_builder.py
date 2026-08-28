import os
import instructor
from groq import Groq
from src.schemas import CandidateProfile

def build_profile(resume_text: str, transcript_text: str, target_role_name: str) -> CandidateProfile:
    """
    Calls the LLM to extract a CandidateProfile from the resume and transcript.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    client = instructor.from_groq(Groq(api_key=api_key), mode=instructor.Mode.JSON)

    system_prompt = """You are a factual extraction engine for a hiring pipeline. You do not form opinions,
scores, or recommendations. Your only job is to read a resume and an interview
transcript and extract a structured, evidence-linked profile.

Rules:
1. Every field you populate must carry the exact quote it came from. Never
   paraphrase a quote — copy it verbatim from the source text.
2. If a claim on the resume is contradicted, clarified, or walked back in the
   transcript, capture BOTH the original claim and the transcript's version as
   separate entries, and do not silently resolve the conflict yourself — that is
   the downstream agents' job.
3. For every quantifiable claim (percentages, counts, time savings), check whether
   the transcript explains HOW it was measured. If the candidate describes it as
   informal, a guess, or "haven't verified" in the transcript, set
   verification_status to "self_reported_informal". If no measurement method is
   given anywhere, set it to "unverified". Only use "verified" if a concrete
   measurement method is described.
4. For self_disclosed_gaps, set self_disclosed=true only if the candidate raised
   the gap themselves, unprompted by a direct skeptical question pointing it out.
   If the interviewer had to confront them with it first, set self_disclosed=false
   and note that in context.
5. Do not infer motivation, honesty, or competence. That is not your job here.
6. If information needed for a field is simply absent, omit that entry rather than
   inventing one.

Output must validate against the CandidateProfile schema. Return JSON only."""

    user_message = f"""Target Role: {target_role_name}

=== RESUME ===
{resume_text}

=== TRANSCRIPT ===
{transcript_text}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        response_model=CandidateProfile,
        temperature=0.0
    )

    return response

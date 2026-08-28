import os
import uuid
import instructor
from groq import Groq
from src.schemas import AgentOpinion, Tension, DebateTurn
from src.agents.runner import load_persona_prompt

DEBATE_ADDENDUM = """
Another reviewer on this panel raised a specific point that may bear on your
opinion. You are not shown their full opinion — only this one claim, so that you
evaluate it on its own merits rather than deferring to their overall verdict.

Their claim: "{source_claim}"
Their supporting quote: "{source_quote}"

Respond with exactly one of:
- "rebut": you have your own evidence that this claim doesn't change your
  assessment. Provide it with a verbatim quote.
- "concede": this claim changes your opinion. State your new verdict and/or
  confidence, and explain what specifically changed your mind.
- "partial_agree": the claim is valid but only partially affects your assessment.
  Explain what changes and what doesn't.

Do not concede just to appear collaborative, and do not rebut just to defend your
first answer. Change your mind only if the evidence actually warrants it.

Output must validate against the DebateTurn schema (response_type,
response_evidence, prior_verdict, new_verdict, prior_confidence, new_confidence).
Return JSON only.
"""

def run_debate_turn(tension: Tension, opinions_dict: dict, round_num: int, target_agent, source_agent) -> DebateTurn:
    """
    Executes a single debate turn by calling the target agent LLM.
    We pass in the specific target_agent and source_agent to allow both sides to respond.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    client = instructor.from_groq(Groq(api_key=api_key), mode=instructor.Mode.JSON)
    
    # In some tension types we might swap them to make sense, but for now fixed.
    source_opinion = opinions_dict[source_agent]
    target_opinion = opinions_dict[target_agent]
    
    # We need the source_quote. 
    # For simplicity, we just use tension.claim_a as the source claim.
    # To get the quote, we find the evidence item in source_opinion that matches claim_a.
    source_quote = ""
    for ev in source_opinion.evidence:
        if ev.claim == tension.claim_a:
            source_quote = ev.quote
            break
            
    persona_prompt = load_persona_prompt(target_agent)
    system_prompt = persona_prompt + "\n" + DEBATE_ADDENDUM.format(
        source_claim=tension.claim_a,
        source_quote=source_quote
    )

    user_message = f"""=== YOUR PRIOR OPINION ===
{target_opinion.model_dump_json(indent=2)}
"""

    turn: DebateTurn = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        response_model=DebateTurn,
        temperature=0.0
    )
    turn.turn_id = str(uuid.uuid4())
    turn.round = round_num
    turn.tension_id = tension.tension_id
    turn.source_agent = source_agent
    turn.target_agent = target_agent
    turn.source_claim = tension.claim_a
    turn.source_quote = source_quote
    
    # Override prior states to ensure consistency
    turn.prior_verdict = target_opinion.verdict
    turn.prior_confidence = target_opinion.confidence

    return turn

def apply_revision(opinion: AgentOpinion, turn: DebateTurn) -> AgentOpinion:
    """
    Applies the debate turn to the original opinion, creating a new updated opinion object.
    """
    new_opinion = opinion.model_copy(deep=True)
    new_opinion.opinion_id = str(uuid.uuid4())
    new_opinion.round = turn.round
    new_opinion.revision_of = opinion.opinion_id
    new_opinion.revision_reason = f"Response type: {turn.response_type.value}"
    
    if turn.new_verdict:
        new_opinion.verdict = turn.new_verdict
    if turn.new_confidence:
        new_opinion.confidence = turn.new_confidence
        
    # We could add the response evidence to the new opinion's evidence
    new_opinion.evidence.extend(turn.response_evidence)
    
    return new_opinion

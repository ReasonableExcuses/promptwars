import re
from thefuzz import fuzz
from src.schemas import AgentOpinion, DebateTurn

def normalize_whitespace(text: str) -> str:
    """Normalizes whitespace by replacing multiple spaces/newlines with a single space."""
    return re.sub(r'\s+', ' ', text).strip()

def verify_evidence(opinion: AgentOpinion, source_text: str) -> AgentOpinion:
    """
    Verifies that quotes in the AgentOpinion's evidence match the source text.
    Mutates and returns the opinion.
    """
    normalized_source = normalize_whitespace(source_text.lower())
    for item in opinion.evidence:
        normalized_quote = normalize_whitespace(item.quote.lower())
        if normalized_quote in normalized_source:
            item.verified = True
        elif fuzz.partial_ratio(normalized_quote, normalized_source) > 92:
            item.verified = True   # tolerate minor OCR/whitespace drift, not paraphrase
        else:
            item.verified = False
    return opinion

def verify_evidence_on_turn(turn: DebateTurn, source_text: str) -> DebateTurn:
    """
    Verifies that quotes in a DebateTurn's response_evidence match the source text.
    Mutates and returns the turn.
    """
    normalized_source = normalize_whitespace(source_text.lower())
    for item in turn.response_evidence:
        normalized_quote = normalize_whitespace(item.quote.lower())
        if normalized_quote in normalized_source:
            item.verified = True
        elif fuzz.partial_ratio(normalized_quote, normalized_source) > 92:
            item.verified = True   # tolerate minor OCR/whitespace drift, not paraphrase
        else:
            item.verified = False
    return turn

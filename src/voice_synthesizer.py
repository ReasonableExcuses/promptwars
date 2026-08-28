import os
import tempfile
from gtts import gTTS
from src.schemas import DebateTurn

# Map each persona to a different regional accent
AGENT_ACCENT_MAP = {
    "technical": "co.uk",      # British
    "culture": "com.au",       # Australian
    "hiring_manager": "com",   # American
    "skeptic": "co.in"         # Indian
}

def generate_debate_audio(debate_log: list, output_path: str):
    """
    Generates a single MP3 file containing the voice debate.
    Each agent reads their own turns using a distinct accent.
    debate_log can be a list of DebateTurn objects or dicts (if loaded from JSON).
    """
    temp_files = []
    
    try:
        # Generate introductory audio
        intro_text = "Prompt Wars Debate Session. Commencing cross-examination."
        intro_tts = gTTS(text=intro_text, lang='en', tld='com')
        intro_path = os.path.join(tempfile.gettempdir(), "intro.mp3")
        intro_tts.save(intro_path)
        temp_files.append(intro_path)

        for i, turn in enumerate(debate_log):
            # Support both Pydantic models and raw dicts
            is_dict = isinstance(turn, dict)
            
            target_agent = turn['target_agent'] if is_dict else turn.target_agent.value
            source_agent = turn['source_agent'] if is_dict else turn.source_agent.value
            response_type = turn['response_type'] if is_dict else turn.response_type.value
            response_evidence = turn['response_evidence'] if is_dict else turn.response_evidence
            new_verdict = turn.get('new_verdict') if is_dict else turn.new_verdict
            
            tld = AGENT_ACCENT_MAP.get(target_agent, 'com')
            
            # Construct a human-readable script for the turn
            response = response_type.replace('_', ' ')
            script = f"{target_agent.replace('_', ' ')} agent responding to {source_agent.replace('_', ' ')}. "
            script += f"I choose to {response}. "
            
            if response_evidence:
                script += "My evidence is: "
                for ev in response_evidence:
                    claim = ev['claim'] if isinstance(ev, dict) else ev.claim
                    script += f"{claim}. "
            
            if new_verdict:
                verdict_str = new_verdict if isinstance(new_verdict, str) else new_verdict.value
                script += f"My new verdict is {verdict_str.replace('_', ' ')}. "
            
            # Generate audio for this turn
            tts = gTTS(text=script, lang='en', tld=tld)
            turn_path = os.path.join(tempfile.gettempdir(), f"turn_{i}.mp3")
            tts.save(turn_path)
            temp_files.append(turn_path)
        
        # Concatenate MP3s
        with open(output_path, 'wb') as outfile:
            for f in temp_files:
                with open(f, 'rb') as infile:
                    outfile.write(infile.read())
                    
    finally:
        # Cleanup temp files
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    return output_path

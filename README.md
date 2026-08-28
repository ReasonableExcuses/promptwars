# Multi-Agent AI Interview Panel Simulator

This project is an advanced multi-agent evaluation system designed to simulate a real-world hiring panel. It uses multiple distinct AI personas to evaluate a candidate based on their resume and an interview transcript against a specific job description.

## Features

- **Profile Building**: Extracts factual claims, timelines, and skills from a candidate's resume and interview transcript.
- **Independent Agent Personas**: Uses four distinct personas (Technical, Culture, Hiring Manager, Skeptic) to form initial independent opinions without shared context.
- **Evidence Verification**: Validates all agent quotes against the source documents using fuzzy string matching, preventing AI hallucinations.
- **Tension Detection & Debate Engine**: Automatically detects contradictions or disagreements between agents and forces them to debate specific claims, leading to revisions or concessions.
- **Decision Synthesis**: A panel chair agent synthesizes the final post-debate opinions into a coherent hiring recommendation.
- **Free Execution**: Uses the `instructor` library with `Groq` to execute LLM calls entirely for free using high-quality open models (`openai/gpt-oss-120b`).

## Project Structure

- `app.py`: Main CLI entry point.
- `src/`: Core logic including agent runner, profile builder, debate engine, tension detection, and synthesis.
- `src/schemas.py`: Strict Pydantic models enforcing structured LLM outputs.
- `src/agents/prompts/`: Persona instructions for the various agents.
- `data/`: Contains the job description and candidate source documents (Resumes & Transcripts).
- `tests/`: Unit tests (e.g., verifying fuzzy matching and tension detection).
- `runs/`: Output directory where all intermediate JSON artifacts (opinions, debate logs, profiles) and final reports are stored.

## Installation

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # Windows
   source venv/bin/activate      # Mac/Linux
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set your Groq API Key:
   ```bash
   $env:GROQ_API_KEY="gsk_..."
   ```

## Usage

Run the end-to-end pipeline via the CLI application:

```bash
python app.py --candidate ALL
```

You can also run for a specific candidate:
```bash
python app.py --candidate A
```

All final reports (`*_final_report.md`) and intermediate agent states will be written to the `runs/` directory.

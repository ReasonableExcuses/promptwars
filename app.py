import argparse
import sys
from src.orchestrator import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent AI Interview Panel Simulator")
    parser.add_argument("--candidate", type=str, choices=["A", "B", "ALL"], default="ALL",
                        help="Which candidate to run (A, B, or ALL)")
    
    args = parser.parse_args()

    # Load data
    with open("data/job_description.txt", "r", encoding="utf-8") as f:
        jd_text = f.read()

    candidates_to_run = []
    
    if args.candidate in ["A", "ALL"]:
        with open("data/candidate_a_resume.txt", "r", encoding="utf-8") as f:
            res_a = f.read()
        with open("data/candidate_a_transcript.txt", "r", encoding="utf-8") as f:
            trans_a = f.read()
        candidates_to_run.append({
            "candidate_id": "Candidate_A",
            "name": "Rohan Malhotra",
            "resume_text": res_a,
            "transcript_text": trans_a,
            "jd_text": jd_text
        })

    if args.candidate in ["B", "ALL"]:
        with open("data/candidate_b_resume.txt", "r", encoding="utf-8") as f:
            res_b = f.read()
        with open("data/candidate_b_transcript.txt", "r", encoding="utf-8") as f:
            trans_b = f.read()
        candidates_to_run.append({
            "candidate_id": "Candidate_B",
            "name": "Ananya Iyer",
            "resume_text": res_b,
            "transcript_text": trans_b,
            "jd_text": jd_text
        })

    print(f"Starting pipeline for {len(candidates_to_run)} candidate(s)...")
    
    for c in candidates_to_run:
        report = run_pipeline(**c)
        print("\n" + "="*80)
        print(report)
        print("="*80 + "\n")

if __name__ == "__main__":
    main()

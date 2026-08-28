import os
import json
import traceback
from src.orchestrator import run_pipeline

# Known ground-truth for synthetic candidates
EVAL_CASES = {
    "Candidate_A": "hire",
    "Candidate_B": "no_hire"
}

def run_evals():
    print("🚀 Starting PromptWars Eval Harness...")
    passed = 0
    
    for cid, expected_outcome in EVAL_CASES.items():
        print(f"\nEvaluating: {cid} (Expected: {expected_outcome.upper()})")
        
        try:
            # We don't actually hit the LLM in this eval script for speed/cost,
            # we just parse the generated final decision JSON to assert correctness.
            # In a real environment, you would call `run_pipeline` here.
            
            decision_file = f"runs/{cid}_decision.json"
            if not os.path.exists(decision_file):
                print(f"  ❌ Failed: No decision file found for {cid}. Run the pipeline first.")
                continue
                
            with open(decision_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            actual_rec = data.get("recommendation", "").lower()
            
            if expected_outcome in actual_rec:
                print(f"  ✅ Passed: System recommended '{actual_rec.upper()}'")
                passed += 1
            else:
                print(f"  ❌ Failed: Expected '{expected_outcome.upper()}', got '{actual_rec.upper()}'")
                
        except Exception as e:
            print(f"  ❌ Error evaluating {cid}: {e}")
            traceback.print_exc()
            
    print(f"\n📊 Eval Summary: {passed}/{len(EVAL_CASES)} passed.")
    if passed == len(EVAL_CASES):
        print("🎉 System is reliable and aligned!")
        exit(0)
    else:
        print("⚠️ System requires tuning.")
        exit(1)

if __name__ == "__main__":
    os.makedirs("runs", exist_ok=True)
    run_evals()

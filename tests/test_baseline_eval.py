import subprocess, sys, pathlib

def test_baseline_recall_gate():
    subprocess.run([sys.executable, "scripts/eval_retrieval.py", "--use_reranker"], check=True)
    p = pathlib.Path("eval_results.jsonl")
    assert p.exists(), "eval_results.jsonl not found"
    lines = p.read_text().strip().splitlines()
    assert len(lines) >= 10, "not enough eval rows; ingest catalog first"

import json
import subprocess
import sys
from pathlib import Path

from app.provenance import canonicalize_provenance_bytes, compute_provenance_hash


EXAMPLE_PATH = Path("examples") / "sample_provenance.json"
FIXTURE_PATH = Path("tests") / "fixtures" / "sample_contract.txt"


def test_canonical_bytes_are_stable():
    payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    first = canonicalize_provenance_bytes(payload)
    second = canonicalize_provenance_bytes(payload)
    assert first == second
    assert payload["provenance_hash"] == compute_provenance_hash(payload)


def test_one_character_change_causes_mismatch():
    payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    tampered = dict(payload)
    tampered["language"] = "fr"
    assert compute_provenance_hash(tampered) != payload["provenance_hash"]


def test_verify_provenance_cli_matches_example():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_provenance.py",
            "--provenance",
            str(EXAMPLE_PATH),
            "--file",
            str(FIXTURE_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "MATCH" in completed.stdout


def test_verify_provenance_cli_fails_on_tamper(tmp_path):
    payload = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    payload["language"] = "fr"
    tampered_path = tmp_path / "tampered.json"
    tampered_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/verify_provenance.py",
            "--provenance",
            str(tampered_path),
            "--file",
            str(FIXTURE_PATH),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "MISMATCH" in completed.stdout

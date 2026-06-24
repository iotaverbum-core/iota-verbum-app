#!/usr/bin/env python3
"""IOTA VERBUM Workbench v0.2.

A local cockpit for feeding evidence into IOTA and watching it become a
trace, verifier decision, ledger record, and replay-derived world model.

Run:
    python iota_workbench.py
Open:
    http://localhost:8765
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "iota_manifest.json"
RUN_DIR = ROOT / "workbench_runs"
LEDGER_PATH = RUN_DIR / "ledger.jsonl"
PORT = 8765


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalise(text: str) -> str:
    return " ".join(text.replace("\r", "\n").split())


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "name": "IOTA VERBUM WORKBENCH",
        "purpose": "Protect truth across AI-assisted reasoning by separating evidence, verification, ledger commit, and replay-derived world state.",
        "operating_sentence": "I do not treat generated text as authority. I treat evidence, verification, ledger commit, and replay-derived world state as authority.",
        "authority": ["sealed evidence", "deterministic verifier", "append-only ledger", "replay-derived world model"],
        "not_authority": ["chat text", "unverified suggestions", "generated summaries without trace data"],
        "core_pipeline": ["Feed", "EvidencePack", "ClaimGraph", "Verifier", "Ledger", "World Model"],
        "first_questions": ["What are you built to do?", "What should I feed you?", "What do you trust?", "Show me the world model.", "What did the verifier see?"],
    }


@dataclass(frozen=True)
class Stage:
    id: str
    title: str
    summary: str
    status: str
    data: object


@dataclass(frozen=True)
class LedgerRecord:
    record_id: str
    created_at: str
    category: str
    title: str
    evidence_hash: str
    claim_graph_hash: str
    provenance_hash: str
    verifier_status: str
    authority_effect: str
    trace: dict


def classify(text: str) -> str:
    raw = text.strip()
    lower = raw.lower()
    if not raw:
        return "empty"
    if raw.startswith("{") and raw.endswith("}"):
        return "json_report"
    if any(word in lower for word in ["iota verbum", "generated text is not authority", "verifier", "ledger", "world model", "neurosymbolic", "evidencepack", "claimgraph"]):
        return "architecture"
    if any(word in lower for word in ["agreement", "governed by", "terminate", "confidential", "liability", "contract", "nda"]):
        return "legal_document"
    if any(word in lower for word in ["sfa", "prior state", "benchmark", "truncation", "verdict", "score"]):
        return "experiment_report"
    return "general_evidence"


def sentence_claims(text: str, category: str) -> list[dict]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = []
    for idx, sentence in enumerate(sentences[:8], start=1):
        sentence = sentence.strip()
        if not sentence:
            continue
        claims.append({
            "id": f"claim_{idx}",
            "type": "recorded_statement",
            "category": category,
            "value": sentence,
            "grounding": sentence,
            "truth_status": "recorded_as_evidence_not_external_certification",
        })
    return claims


def legal_claims(text: str) -> list[dict]:
    claims = []
    law = re.search(r"governed by the laws? of ([A-Za-z ,.-]+)", text, re.IGNORECASE)
    if law:
        claims.append({"id": "legal_governing_law", "type": "governing_law", "value": law.group(1).strip().rstrip("."), "grounding": law.group(0), "truth_status": "grounded_in_document_text"})
    term = re.search(r"terminate[^.]{0,140}", text, re.IGNORECASE)
    if term:
        claims.append({"id": "legal_termination", "type": "termination", "value": term.group(0).strip(), "grounding": term.group(0), "truth_status": "grounded_in_document_text"})
    if "confidential" in text.lower():
        start = max(0, text.lower().find("confidential") - 80)
        span = text[start:start + 220].strip()
        claims.append({"id": "legal_confidentiality", "type": "confidentiality", "value": "confidentiality language detected", "grounding": span, "truth_status": "grounded_in_document_text"})
    if "liability" in text.lower():
        start = max(0, text.lower().find("liability") - 80)
        span = text[start:start + 220].strip()
        claims.append({"id": "legal_liability", "type": "liability", "value": "liability language detected", "grounding": span, "truth_status": "grounded_in_document_text"})
    return claims


def build_claim_graph(text: str, category: str) -> dict:
    claims = []
    if category == "legal_document":
        claims.extend(legal_claims(text))
    claims.extend(sentence_claims(text, category))
    return {
        "schema": "iota.claim_graph.v0.2",
        "category": category,
        "claim_count": len(claims),
        "claims": claims,
        "interpretation_note": "The workbench records fed evidence. It does not certify external truth unless a later verifier proves it.",
    }


def title_from(text: str, category: str) -> str:
    clean = text.strip().replace("\n", " ")
    if not clean:
        return "Empty input"
    return f"{category}: {clean[:70]}"


def build_trace(text: str, filename: str) -> tuple[dict, LedgerRecord]:
    text = normalise(text)
    category = classify(text)
    evidence_pack = {
        "schema": "iota.evidence_pack.v0.2",
        "filename": filename,
        "category": category,
        "normalisation": "whitespace collapse, utf-8 text",
        "evidence_hash": sha256_text(text),
        "text_preview": text[:1200],
    }
    claim_graph = build_claim_graph(text, category)
    claim_graph_hash = sha256_text(canonical_json(claim_graph))
    verifier_status = "rejected" if category == "empty" else "accepted_as_evidence"
    authority_effect = "ledger_record_only" if category != "legal_document" else "ledger_record_and_document_claims"
    verifier = {
        "status": verifier_status,
        "authority_effect": authority_effect,
        "received": ["evidence_hash", "category", "claim_graph", "claim_graph_hash"],
        "excluded": ["chat_intent", "assistant_confidence", "unverified_external_truth", "model_generated_memory"],
        "rule": "A fed statement may be recorded as evidence; it is not automatically certified as external truth.",
    }
    provenance = {
        "schema": "iota.provenance.v0.2",
        "created_at": utc_now(),
        "category": category,
        "evidence_hash": evidence_pack["evidence_hash"],
        "claim_graph_hash": claim_graph_hash,
        "verifier_status": verifier_status,
        "authority_effect": authority_effect,
    }
    provenance_hash = sha256_text(canonical_json(provenance))
    record_id = "ivr_" + uuid.uuid4().hex[:16]
    stages = [
        Stage("feed", "Feed", "You fed the system evidence. It did not secretly train a model.", "complete", {"filename": filename, "category": category, "chars": len(text)}),
        Stage("evidence", "EvidencePack", "The input was normalised and sealed with a hash.", "complete", evidence_pack),
        Stage("claims", "ClaimGraph", "The workbench turned the evidence into typed, grounded claims.", "complete", claim_graph),
        Stage("firewall", "Verifier Firewall", "The verifier saw evidence and claims, not chat confidence or generated memory.", "pass", verifier),
        Stage("verify", "Verifier Decision", "The input was accepted as evidence or rejected before world-state replay.", "pass" if verifier_status != "rejected" else "warn", verifier),
        Stage("ledger", "Ledger", "The record was appended to the local ledger.", "pass", {"record_id": record_id, "provenance_hash": provenance_hash, "ledger": "workbench_runs/ledger.jsonl"}),
        Stage("world", "World Model", "The visible world model grows by replaying accepted ledger records.", "pass", {"effect": authority_effect, "category": category}),
    ]
    trace = {"schema": "iota.trace.v0.2", "record_id": record_id, "stages": [asdict(stage) for stage in stages]}
    record = LedgerRecord(record_id, provenance["created_at"], category, title_from(text, category), evidence_pack["evidence_hash"], claim_graph_hash, provenance_hash, verifier_status, authority_effect, trace)
    return trace, record


def append_ledger(record: LedgerRecord) -> None:
    RUN_DIR.mkdir(exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(canonical_json(asdict(record)) + "\n")


def read_ledger() -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    rows = []
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def world_model() -> dict:
    records = [r for r in read_ledger() if r.get("verifier_status") != "rejected"]
    by_category: dict[str, int] = {}
    for r in records:
        by_category[r.get("category", "unknown")] = by_category.get(r.get("category", "unknown"), 0) + 1
    return {
        "schema": "iota.world_model.v0.2",
        "authority": "replay-derived from accepted ledger evidence",
        "record_count": len(records),
        "by_category": by_category,
        "recent_records": [{"record_id": r.get("record_id"), "category": r.get("category"), "title": r.get("title"), "effect": r.get("authority_effect")} for r in records[-20:]],
    }


def answer_question(question: str) -> dict:
    manifest = load_manifest()
    q = question.lower()
    if "feed" in q:
        return {"answer": "Feed me anchors first: identity, architecture, verifier boundary, legal examples, benchmark reports, and known failures. Each feed becomes evidence, not secret training.", "detail": {"recommended_order": ["identity", "architecture", "boundary", "sample legal document", "benchmark report", "known bad claim"]}}
    if "trust" in q or "authority" in q:
        return {"answer": "I trust replayed ledger evidence, not generated text.", "detail": {"authority": manifest.get("authority", []), "not_authority": manifest.get("not_authority", [])}}
    if "world" in q or "state" in q:
        return {"answer": "The world model is rebuilt from accepted ledger records.", "detail": world_model()}
    if "verifier" in q or "firewall" in q:
        return {"answer": "The verifier sees evidence hashes and claim graphs. It excludes chat intent, assistant confidence, and generated memory.", "detail": {"boundary": "chat may propose; verifier judges; ledger remembers"}}
    if "pipeline" in q:
        return {"answer": "The pipeline is Feed -> EvidencePack -> ClaimGraph -> Verifier Firewall -> Verifier Decision -> Ledger -> World Model.", "detail": {"pipeline": ["Feed", "EvidencePack", "ClaimGraph", "Verifier Firewall", "Verifier Decision", "Ledger", "World Model"]}}
    return {"answer": manifest.get("purpose", "IOTA protects truth through verified evidence.") + " " + manifest.get("operating_sentence", ""), "detail": manifest}


def inspect_report(raw: str) -> dict:
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"answer": f"Invalid JSON report: {exc.msg}", "detail": {}}
    comparisons = report.get("comparisons", []) if isinstance(report.get("comparisons", []), list) else []
    wins = [x for x in comparisons if x.get("meaningful_true_prior_state_win") is True]
    return {"answer": f"Verdict: {report.get('prior_state_verdict', report.get('verdict', 'unknown'))}. Reason: {report.get('verdict_reason', 'not provided')}. Truncation: {report.get('any_truncation', 'not provided')}. Meaningful true Prior State wins: {len(wins)}/{len(comparisons)}.", "detail": {"verdict": report.get("prior_state_verdict", report.get("verdict", "unknown")), "verdict_reason": report.get("verdict_reason"), "any_truncation": report.get("any_truncation"), "comparison_count": len(comparisons), "meaningful_true_prior_state_wins": len(wins)}}


def page(content: str) -> bytes:
    m = load_manifest()
    pills = "".join("<span class='pill'>" + html.escape(str(x)) + "</span>" for x in m.get("authority", []))
    body = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>IOTA Workbench</title><style>body{{margin:0;background:#050814;color:#eef7ff;font-family:Arial,Helvetica,sans-serif}}.wrap{{max-width:1280px;margin:auto;padding:28px}}.hero,.panel{{border:1px solid #21445a;background:#081526;border-radius:22px;padding:22px;margin:0 0 18px}}h1{{font-size:52px;margin:8px 0}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}textarea,input,select{{width:100%;box-sizing:border-box;background:#020617;color:#eef7ff;border:1px solid #334155;border-radius:12px;padding:12px;margin:4px 0}}textarea{{min-height:150px}}button{{background:#22d3ee;color:#042f2e;border:0;border-radius:12px;padding:12px 16px;font-weight:800;margin-top:8px}}pre{{white-space:pre-wrap;word-break:break-word;background:#020617;border:1px solid #334155;border-radius:14px;padding:14px;max-height:620px;overflow:auto}}.pill{{display:inline-block;border:1px solid #16a34a;border-radius:999px;padding:6px 10px;margin:3px;color:#dcfce7}}.stage{{border:1px solid #334155;border-radius:16px;padding:12px;margin:10px 0;background:#0f172a}}.pass{{border-color:#22c55e}}.warn{{border-color:#f59e0b}}@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><div class='wrap'><section class='hero'><strong>Feed it evidence. Watch it grow by ledger replay.</strong><h1>{html.escape(m.get('name','IOTA VERBUM'))}</h1><p>{html.escape(m.get('operating_sentence',''))}</p>{pills}</section>{content}</div></body></html>"""
    return body.encode("utf-8")


def home(answer: dict | None = None, trace: dict | None = None, report: dict | None = None) -> bytes:
    questions = "".join("<option>" + html.escape(q) + "</option>" for q in load_manifest().get("first_questions", []))
    answer_html = "" if not answer else f"<section class='panel'><h2>Answer</h2><p>{html.escape(answer.get('answer',''))}</p><pre>{html.escape(json.dumps(answer.get('detail',{}), indent=2))}</pre></section>"
    report_html = "" if not report else f"<section class='panel'><h2>Report inspection</h2><p>{html.escape(report.get('answer',''))}</p><pre>{html.escape(json.dumps(report.get('detail',{}), indent=2))}</pre></section>"
    if trace:
        trace_html = "".join(f"<div class='stage {html.escape(s.get('status',''))}'><h3>{html.escape(s.get('title',''))}</h3><p>{html.escape(s.get('summary',''))}</p><pre>{html.escape(json.dumps(s.get('data'), indent=2))}</pre></div>" for s in trace.get("stages", []))
    else:
        trace_html = "<p>No feed run yet. Paste an anchor or a document below.</p>"
    content = f"""
<div class='grid'><section class='panel'><h2>Talk to IOTA</h2><form method='post' action='/chat'><select name='question'>{questions}</select><input name='custom' placeholder='Or type your own question'><button>Ask</button></form></section><section class='panel'><h2>World Model</h2><pre>{html.escape(json.dumps(world_model(), indent=2))}</pre></section></div>
{answer_html}
<section class='panel'><h2>Feed IOTA</h2><form method='post' action='/feed'><input name='filename' value='feed.txt'><textarea name='text'>IOTA VERBUM is built to protect truth across AI-assisted reasoning. Generated text is not authority. Evidence, verification, ledger commit, and replay-derived world state are authority.</textarea><button>Feed and Trace</button></form></section>
<section class='panel'><h2>Pipeline Trace</h2>{trace_html}</section>
<section class='panel'><h2>JSON Report Inspector</h2><form method='post' action='/report'><textarea name='report' placeholder='Paste JSON report here'></textarea><button>Inspect Report</button></form></section>{report_html}
"""
    return page(content)


class Handler(BaseHTTPRequestHandler):
    def send_html(self, payload: bytes, status: int = 200) -> None:
        self.send_response(status); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
    def send_json(self, payload: object, status: int = 200) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8"); self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def form(self) -> dict[str, str]:
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8"); return {k: v[0] for k, v in parse_qs(raw).items()}
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/world": self.send_json(world_model())
        elif path == "/self-test": self.send_json({"ok": True, "world_model": world_model()})
        else: self.send_html(home())
    def do_POST(self) -> None:
        path = urlparse(self.path).path; data = self.form()
        if path == "/chat": self.send_html(home(answer=answer_question(data.get("custom") or data.get("question") or "What are you built to do?")))
        elif path in ["/feed", "/run"]:
            trace, record = build_trace(data.get("text", ""), data.get("filename", "feed.txt")); append_ledger(record); self.send_html(home(trace=trace, answer={"answer": f"Feed complete. Category: {record.category}. Record {record.record_id} was {record.verifier_status}. World effect: {record.authority_effect}.", "detail": asdict(record)}))
        elif path == "/report": self.send_html(home(report=inspect_report(data.get("report", ""))))
        else: self.send_html(home(answer={"answer": "Unknown route", "detail": {}}), 404)
    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write("[iota-workbench] " + (fmt % args) + "\n")


def main() -> int:
    if "--self-test" in sys.argv:
        print(json.dumps({"ok": True, "manifest": load_manifest().get("name"), "world_model": world_model()}, indent=2)); return 0
    RUN_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"IOTA VERBUM Workbench v0.2 running at http://localhost:{PORT}")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nShutting down."); time.sleep(0.1)
    finally: server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

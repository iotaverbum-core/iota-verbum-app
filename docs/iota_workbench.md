# IOTA VERBUM Workbench

Run the local workbench:

```bash
python iota_workbench.py
```

Open:

```text
http://localhost:8765
```

Self-test:

```bash
python iota_workbench.py --self-test
```

## Purpose

The workbench gives IOTA VERBUM a visible end-to-end surface:

1. orientation from `iota_manifest.json`
2. local text input
3. EvidencePack construction
4. ClaimGraph extraction
5. verifier firewall view
6. ledger append to `workbench_runs/ledger.jsonl`
7. replay-derived world model
8. JSON report inspection

## Authority rule

Generated text is not authority. Evidence, verification, ledger commit, and replay-derived world state are authority.

## Scope

This is a local file-backed cockpit. It does not require a database, provider key, build chain, or deployment migration.

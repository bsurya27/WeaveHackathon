"""Build journey.html by pulling the latest agent trace from W&B Weave.

This replaces the old local-JSON build path: instead of reading
sessions/<id>.json, this script queries Weave for the trace produced
by the agent pipeline (same data Weave records via @weave.op) and
reconstructs the session shape that journey_template_v2.html expects.

Usage:
    python build_journey.py
        # uses the most recent 'run' trace from the project
    python build_journey.py --trace-id <id>
        # uses a specific trace
    python build_journey.py --project entity/project
        # override the default project
    python build_journey.py --save-json out.json
        # also save the reconstructed session JSON to disk

Requirements:
    pip install weave wandb
    wandb login   (or set WANDB_API_KEY env var)

Architecture this expects (matches the existing @weave.op tree):

    run
     ├─ run_specialists
     │   ├─ marketer
     │   ├─ legal
     │   ├─ tech
     │   └─ finance
     ├─ run_decider_stage1
     │   ├─ investor
     │   ├─ devils_advocate
     │   └─ innovator
     ├─ run_decider_stage2
     │   ├─ investor
     │   ├─ devils_advocate
     │   └─ innovator
     └─ synthesis

If the op names in your pipeline differ, change the constants below.
"""
import argparse
import json
from pathlib import Path

import weave

ROOT = Path(__file__).parent
DEFAULT_PROJECT = "weavehackathon/startup-advisor"

# Op-name constants — adjust here if pipeline ops are renamed
ROOT_OP = "run"
SPECIALIST_PARENT_OP = "run_specialists"
STAGE1_PARENT_OP = "run_decider_stage1"
STAGE2_PARENT_OP = "run_decider_stage2"
SYNTHESIS_OP = "synthesis"
SPECIALIST_ROLES = ["marketer", "legal", "tech", "finance"]
DECIDER_ROLES = ["investor", "devils_advocate", "innovator"]


def _short_name(op_name: str) -> str:
    """Strip module/version qualifiers.

    'mypkg.module:marketer:v3' -> 'marketer'
    'mypkg/module/run'         -> 'run'
    """
    if not op_name:
        return ""
    n = op_name
    # Drop trailing version segments like ':v1', ':v12'
    if ":" in n:
        parts = n.split(":")
        parts = [p for p in parts if not (p.startswith("v") and p[1:].isdigit())]
        n = parts[-1] if parts else n
    if "/" in n:
        n = n.split("/")[-1]
    if "." in n:
        n = n.split(".")[-1]
    return n


def _ensure_dict(obj) -> dict:
    """Weave outputs are usually dicts already; be defensive."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):  # pydantic
        return obj.model_dump()
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return {}


def fetch_session_from_weave(project: str, trace_id: str | None = None) -> dict:
    """Pull a 'run' trace from Weave and reshape it for the journey template."""
    print(f"→ weave.init({project!r})")
    client = weave.init(project)

    # 1) Resolve target trace
    if trace_id is None:
        print(f"→ finding latest '{ROOT_OP}' trace…")
        roots = list(client.get_calls(
            filter={"op_names": [ROOT_OP], "trace_roots_only": True},
        ))
        if not roots:
            raise RuntimeError(
                f"No '{ROOT_OP}' traces found in {project}. "
                f"Has the pipeline been run yet?"
            )
        roots.sort(
            key=lambda c: getattr(c, "started_at", None) or "",
            reverse=True,
        )
        root = roots[0]
        trace_id = root.trace_id
    else:
        print(f"→ loading trace {trace_id}…")
        in_trace = list(client.get_calls(filter={"trace_ids": [trace_id]}))
        roots = [c for c in in_trace if c.parent_id is None]
        if not roots:
            raise RuntimeError(f"No root call found for trace {trace_id}")
        root = roots[0]

    # 2) Fetch every call in this trace
    print(f"→ fetching all calls in trace {trace_id}…")
    all_calls = list(client.get_calls(filter={"trace_ids": [trace_id]}))
    print(f"  got {len(all_calls)} calls")

    # 3) Index calls
    by_id = {c.id: c for c in all_calls}
    by_short_op: dict[str, list] = {}
    for c in all_calls:
        by_short_op.setdefault(_short_name(c.op_name), []).append(c)

    def parent_short(c) -> str | None:
        if c.parent_id and c.parent_id in by_id:
            return _short_name(by_id[c.parent_id].op_name)
        return None

    # 4) Assemble session in the shape journey_template_v2.html expects
    session: dict = {"session_id": (trace_id or "weave")[:12]}

    # pitch_deck — from root's inputs
    inputs = _ensure_dict(getattr(root, "inputs", {}))
    pitch = None
    for k in ("pitch_deck", "deck", "pitch"):
        if k in inputs and isinstance(inputs[k], dict):
            pitch = inputs[k]
            break
    if pitch is None:
        # Fallback: any dict input that looks like a deck
        for v in inputs.values():
            v_dict = _ensure_dict(v)
            if "problem" in v_dict or "solution" in v_dict:
                pitch = v_dict
                break
    session["pitch_deck"] = pitch or {}

    # specialist_reports — outputs of the role ops under run_specialists
    session["specialist_reports"] = []
    for role in SPECIALIST_ROLES:
        # Prefer calls whose parent is run_specialists; fall back to any call by that name
        candidates = by_short_op.get(role, [])
        chosen = next(
            (c for c in candidates if parent_short(c) == SPECIALIST_PARENT_OP),
            candidates[0] if candidates else None,
        )
        if chosen is not None:
            out = _ensure_dict(chosen.output)
            out.setdefault("role", role)
            session["specialist_reports"].append(out)

    # decider_stage1 / decider_stage2 — same role ops appear at both stages,
    # so disambiguate by parent op
    session["decider_stage1"] = []
    session["decider_stage2"] = []
    for role in DECIDER_ROLES:
        for c in by_short_op.get(role, []):
            p = parent_short(c)
            out = _ensure_dict(c.output)
            out.setdefault("role", role)
            if p == STAGE1_PARENT_OP:
                session["decider_stage1"].append(out)
            elif p == STAGE2_PARENT_OP:
                session["decider_stage2"].append(out)

    # final_brief — output of synthesis op (or root output as fallback)
    synth_calls = by_short_op.get(SYNTHESIS_OP, [])
    if synth_calls:
        session["final_brief"] = _ensure_dict(synth_calls[0].output)
    else:
        session["final_brief"] = _ensure_dict(getattr(root, "output", {}))

    print(
        f"  reconstructed: "
        f"pitch_deck={'yes' if session['pitch_deck'] else 'no'}, "
        f"specialists={len(session['specialist_reports'])}, "
        f"d1={len(session['decider_stage1'])}, "
        f"d2={len(session['decider_stage2'])}, "
        f"brief={'yes' if session['final_brief'].get('focus_list') else 'no'}"
    )
    return session


def main():
    p = argparse.ArgumentParser(
        description="Build journey.html from a W&B Weave trace.",
    )
    p.add_argument("--project", default=DEFAULT_PROJECT,
                   help="W&B Weave project (entity/project)")
    p.add_argument("--trace-id", default=None,
                   help="Specific trace ID (default: latest 'run' trace)")
    p.add_argument("--template", default="journey_template_v2.html",
                   help="HTML template path")
    p.add_argument("--output", default="journey.html",
                   help="Output HTML path")
    p.add_argument("--save-json", default=None,
                   help="If set, also save reconstructed session JSON")
    args = p.parse_args()

    session = fetch_session_from_weave(args.project, args.trace_id)

    if args.save_json:
        Path(args.save_json).write_text(
            json.dumps(session, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  saved JSON → {args.save_json}")

    template = (ROOT / args.template).read_text(encoding="utf-8")
    safe_json = json.dumps(session, ensure_ascii=False).replace("</", "<\\/")
    out = template.replace("__SESSION_JSON__", safe_json)
    (ROOT / args.output).write_text(out, encoding="utf-8")
    print(f"  built → {args.output}")


if __name__ == "__main__":
    main()

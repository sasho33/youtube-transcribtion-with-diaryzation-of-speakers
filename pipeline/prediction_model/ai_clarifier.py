# ai_clarifier.py
"""
DeepSeek-powered clarifier for universal predictions (no file overwrite by default).

Tweaks added:
- Deterministic, schema-locked prompt with structured findings and required evidence URLs (≤2 years).
- At least one UI badge + one highlight card if any evidence exists.
- Explicit reason when no adjustment is applied.
- Retry once with a stricter prompt if the initial response lacks structured findings/evidence.
- Silences base predictor stdout/stderr to keep CLI/API output clean.
"""

from __future__ import annotations

import json
import os
import io
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any, Dict, Tuple, Optional, List

# Keep project import path (one level deeper as requested)
sys.path.append(str(Path(__file__).resolve().parents[2]))

# ---------- DeepSeek settings ----------
DEEPSEEK_API_KEY = os.getenv("SHALLOWSEEK_APIK") or os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
TEMPERATURE = 0.0
TOP_P = 1.0
FREQ_PENALTY = 0.0
PRES_PENALTY = 0.0

# Cap rules: default ±30%; allow escalation to ±60% if strong evidence shows a baseline miscalculation.
BASE_MAX_DELTA = 0.30
ESCALATED_MAX_DELTA = 0.60
SUMMARY_MAX_BULLETS = 10
SUMMARY_MIN_BULLETS = 6
NARRATIVE_MIN = 120  # words (advisory)
NARRATIVE_MAX = 180  # words (advisory)
RESEARCH_WINDOW_YEARS = 2


# ---------- Helpers ----------

def _extract_json(text: str) -> Dict[str, Any]:
    """Extract first top-level JSON object from text."""
    try:
        return json.loads(text)
    except Exception:
        pass

    # Fallback: scan for a balanced {...}
    stack = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if stack == 0:
                start = i
            stack += 1
        elif ch == '}':
            stack -= 1
            if stack == 0 and start != -1:
                block = text[start:i+1]
                try:
                    return json.loads(block)
                except Exception:
                    start = -1
    raise ValueError("No valid JSON object found in model response.")


def _normalize_probs(a: float, b: float) -> Tuple[float, float]:
    s = a + b
    if s <= 0:
        return 0.5, 0.5
    return a / s, b / s


def _clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _two_year_window() -> Tuple[str, str]:
    start = (datetime.utcnow() - timedelta(days=365 * RESEARCH_WINDOW_YEARS)).strftime("%Y-%m-%d")
    end = datetime.utcnow().strftime("%Y-%m-%d")
    return start, end


# ---------- Prompt builders ----------

STRICT_FINDINGS_NOTE = (
    "FINDINGS MUST be an array of objects with this shape:\n"
    "  {\n"
    "    id: string,\n"
    "    type: string (one of: recent_result, health_update, logistics, rule_set, ranking, form_note, style_matchup, note),\n"
    "    title: string,\n"
    "    detail: string,\n"
    "    impact: { athlete_name: string (exactly as provided), direction: 'increase'|'decrease'|'neutral', magnitude_pct: integer 0..30, confidence: 'low'|'medium'|'high' },\n"
    "    evidence: [ { url: string, source_title: string, publisher: string, published_at: 'YYYY-MM-DD', retrieved_at: 'YYYY-MM-DD' } ]\n"
    "  }\n"
    "Include at least 2 evidence items across all findings when available; all evidence must be ≤2 years old (prefer latest)."
)

STRICT_UI_NOTE = (
    "Populate ui_highlights with at least one badge and one highlight_card when any evidence exists. "
    "Each badge: { label, type: 'positive'|'info'|'warning', athlete_name, tooltip }. "
    "Each highlight_card: { title, subtitle, snippet, source_url, published_at }."
)

SYSTEM_BASE = (
    "You are a meticulous sports analyst specializing in armwrestling.\n"
    "Return ONLY a JSON object that strictly follows the provided schema.\n"
    "Use deterministic phrasing and stable key order. Do not include markdown fences, comments, or extra text.\n"
    "All probability keys MUST use the exact athlete names provided (no 'athlete1'/'athlete2').\n"
    "Do NOT use placeholder domains (e.g., example.com). Use only real, verifiable URLs with publisher names.\n"
    "Adjustment policy:\n"
    "  • Prefer a non-zero adjustment when any credible finding (medium/high confidence) indicates an advantage; "
    "use a cautious net shift if evidence is mixed (typically ±2–8 percentage points).\n"
    "  • Default cap is ±30 per athlete. However, if strong, recent, well-sourced evidence indicates a baseline "
    "miscalculation (e.g., major injury/health update, decisive recent results, rule/weight change, or ranking swing), "
    "you MAY escalate the cap to ±60 per athlete by setting constraints.max_adjustment_per_athlete_pct = 60 and explain why in adjusted_probabilities.reason.\n"
    f"Use only sources published within the last {RESEARCH_WINDOW_YEARS} years (prefer latest).\n"
    f"Provide {SUMMARY_MIN_BULLETS}–{SUMMARY_MAX_BULLETS} bullet points in 'summary' and a concise {NARRATIVE_MIN}-{NARRATIVE_MAX}-word 'narrative'.\n"
    + STRICT_FINDINGS_NOTE + "\n" + STRICT_UI_NOTE
)


SYSTEM_RETRY_SUFFIX = (
    "\nRETRY MODE: The previous response lacked structured findings/evidence. "
    "This time, you MUST include findings as objects with evidence URLs and dates (≤2 years), "
    "and at least one badge + one highlight_card derived from those findings."
)


def _build_prompts(base_result: Dict[str, Any], strict_retry: bool = False) -> Tuple[str, str, Dict[str, Any]]:
    """Build deterministic system+user prompts for DeepSeek."""
    pred = base_result.get("prediction", {})
    md = base_result.get("match_details", {})

    a1_name = pred.get("athlete1_name", "Athlete A")
    a2_name = pred.get("athlete2_name", "Athlete B")
    before_a = float(pred.get("athlete1_win_probability", 0.5))
    before_b = float(pred.get("athlete2_win_probability", 0.5))

    event_title = md.get("event_title", "(Virtual)")
    event_date = md.get("event_date", datetime.utcnow().strftime("%Y-%m-%d"))
    arm = md.get("match_arm", "Right")
    venue_country = md.get("event_country", "United States")

    as_of_iso = _now_iso()
    start_date, end_date = _two_year_window()

    system_prompt = SYSTEM_BASE + (SYSTEM_RETRY_SUFFIX if strict_retry else "")

    schema_hint = {
        "ai_review": {
            "schema_version": "1.3",
            "as_of": as_of_iso,
            "research_window": {"start_date": start_date, "end_date": end_date},
            "summary": [],
            "narrative": "",
            "adjusted_probabilities": {
                "note": f"Per-athlete cap ±{int(ESCALATED_MAX_DELTA*100)}, sources ≤{RESEARCH_WINDOW_YEARS} years; renormalized to 1.000.",
                "before": {a1_name: round(before_a, 3), a2_name: round(before_b, 3)},
                "deltas": {a1_name: 0.0, a2_name: 0.0},
                "after": {a1_name: round(before_a, 3), a2_name: round(before_b, 3)},
                "cap_applied": False,
                "confidence_tier": "medium",
                "reason": ""  # filled when deltas both 0
            },
            "findings": [],
            "ui_highlights": {"badges": [], "highlight_cards": [], "timeline": []},
            "constraints": {
                "max_adjustment_per_athlete_pct": int(ESCALATED_MAX_DELTA * 100),
                "source_age_limit_years": RESEARCH_WINDOW_YEARS,
                "prefer_latest_sources": True,
                "normalization_rule": "sum_to_one"
            },
            "reproducibility": {
                "model": DEEPSEEK_MODEL,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "frequency_penalty": FREQ_PENALTY,
                "presence_penalty": PRES_PENALTY,
                "response_format": "json",
                "prompt_version": "ai_review:v1.3"
            },
            "meta": {
                "event_title": event_title,
                "event_date": event_date,
                "arm": arm,
                "venue_country": venue_country,
                "athletes": [a1_name, a2_name],
                "generated_at": as_of_iso
            }
        }
    }

    user_prompt = (
        "Base prediction JSON (truncated to essentials):\n"
        + json.dumps(
            {
                "prediction": {
                    "athlete1_name": a1_name,
                    "athlete2_name": a2_name,
                    "athlete1_win_probability": round(before_a, 3),
                    "athlete2_win_probability": round(before_b, 3),
                },
                "match_details": {
                    "event_title": event_title,
                    "event_date": event_date,
                    "match_arm": arm,
                    "event_country": venue_country,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nReturn exactly one JSON object matching this schema and naming convention:\n"
        + json.dumps(schema_hint, ensure_ascii=False, indent=2)
    )

    meta = {
        "a1_name": a1_name,
        "a2_name": a2_name,
        "before_a": before_a,
        "before_b": before_b,
        "as_of_iso": as_of_iso,
        "start_date": start_date,
        "end_date": end_date,
        "event_title": event_title,
        "event_date": event_date,
        "arm": arm,
        "venue_country": venue_country,
    }
    return system_prompt, user_prompt, meta


# ---------- DeepSeek caller ----------

def _call_deepseek(system_prompt: str, user_prompt: str, timeout: int = 60) -> Dict[str, Any]:
    import requests

    if not DEEPSEEK_API_KEY:
        # Fallback: import key lazily from config ONLY if env not set (avoids side effects for most runs)
        try:
            from pipeline.config import SHALLOWSEEK_APIK as _KEY  # type: ignore
            key = _KEY
        except Exception as e:
            raise RuntimeError(
                "DeepSeek API key not found. Set SHALLOWSEEK_APIK (or DEEPSEEK_API_KEY) env var, "
                "or ensure pipeline.config provides SHALLOWSEEK_APIK."
            ) from e
    else:
        key = DEEPSEEK_API_KEY

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "frequency_penalty": FREQ_PENALTY,
        "presence_penalty": PRES_PENALTY,
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=timeout)
    data = resp.json()
    if resp.status_code != 200:
        raise Exception("DeepSeek error:\n" + json.dumps(data, indent=2))

    content = data["choices"][0]["message"]["content"]
    return _extract_json(content)


# ---------- Validation & enrichment ----------
def _evidence_is_valid(e: Dict[str, Any]) -> bool:
    """Reject placeholder or non-HTTP evidence."""
    url = (e or {}).get("url", "").strip().lower()
    if not url.startswith(("http://", "https://")):
        return False
    bad_domains = ("example.com", "localhost", "127.0.0.1")
    return not any(bad in url for bad in bad_domains)


def _evidence_is_fresh(evidence: Dict[str, Any], start_date: str, end_date: str) -> bool:
    if not _evidence_is_valid(evidence):
        return False
    d = (evidence.get("published_at") or "").strip()
    return bool(d) and (start_date <= d <= end_date)



def _ensure_names_in_probs(ap: Dict[str, Any], a1: str, a2: str, before_a: float, before_b: float) -> None:
    for key in ["before", "deltas", "after"]:
        block = ap.get(key, {})
        if "athlete1" in block:
            block[a1] = block.pop("athlete1")
        if "athlete2" in block:
            block[a2] = block.pop("athlete2")
        if a1 not in block:
            block[a1] = (before_a if key != "deltas" else 0.0)
        if a2 not in block:
            block[a2] = (before_b if key != "deltas" else 0.0)
        ap[key] = block

def _parse_date_yyyy_mm_dd(s: str):
        from datetime import datetime
        try:
            return datetime.strptime((s or "").strip(), "%Y-%m-%d")
        except Exception:
            # put unknown/invalid dates at the end
            from datetime import datetime as _dt
            return _dt.min
        
def _populate_min_ui(ui: Dict[str, Any], findings: List[Dict[str, Any]]) -> None:
    if not isinstance(ui.get("badges"), list):
        ui["badges"] = []
    if not isinstance(ui.get("highlight_cards"), list):
        ui["highlight_cards"] = []
    if not isinstance(ui.get("timeline"), list):
        ui["timeline"] = []

    # Add at least one badge + card if we have any finding with valid evidence
    strong = next(
        (f for f in findings if isinstance(f.get("evidence"), list) and len(f["evidence"]) > 0),
        None
    )
    if strong:
        impact = strong.get("impact", {}) or {}
        athlete = impact.get("athlete_name") or "Athlete"
        direction = (impact.get("direction") or "info").lower()
        label = "Recent Form ↑" if direction == "increase" else ("Caution ↓" if direction == "decrease" else "Update")
        tooltip = (strong.get("title") or "Update")[:80]

        if not ui["badges"]:
            ui["badges"].append({
                "label": label,
                "type": "positive" if direction == "increase" else ("warning" if direction == "decrease" else "info"),
                "athlete_name": athlete,
                "tooltip": tooltip
            })

        ev = strong["evidence"][0]
        if not ui["highlight_cards"]:
            ui["highlight_cards"].append({
                "title": strong.get("title") or "Update",
                "subtitle": strong.get("type") or "note",
                "snippet": (strong.get("detail") or "")[:140],
                "source_url": ev.get("url", ""),
                "published_at": ev.get("published_at", "")
            })

    # --- Build a minimal timeline from evidence if empty ---
    if not ui["timeline"]:
        timeline = []
        for f in findings:
            for ev in (f.get("evidence") or []):
                if _evidence_is_valid(ev):  # uses your existing validator
                    timeline.append({
                        "date": ev.get("published_at", ""),
                        "label": f.get("title") or "Update",
                        "source_url": ev.get("url", "")
                    })
        # Sort by date desc and keep top 3
        timeline.sort(key=lambda x: _parse_date_yyyy_mm_dd(x.get("date", "")), reverse=True)
        ui["timeline"] = timeline[:3]

    # --- Sort highlight cards by date desc and keep top 2 (tidy UI) ---
    if ui["highlight_cards"]:
        ui["highlight_cards"].sort(
            key=lambda c: _parse_date_yyyy_mm_dd(c.get("published_at", "")),
            reverse=True
        )
        ui["highlight_cards"] = ui["highlight_cards"][:2]

def _postprocess_and_validate(
    ai_json: Dict[str, Any],
    a1_name: str,
    a2_name: str,
    before_a: float,
    before_b: float,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """Enforce schema correctness, clamp deltas, normalize, ensure names & UI."""
    ai_review = ai_json.get("ai_review", ai_json)

    # Ensure keys
    ai_review.setdefault("schema_version", "1.3")
    ai_review.setdefault("summary", [])
    ai_review.setdefault("narrative", "")
    ai_review.setdefault("adjusted_probabilities", {})
    ai_review.setdefault("findings", [])
    ai_review.setdefault("ui_highlights", {"badges": [], "highlight_cards": [], "timeline": []})
    ai_review.setdefault("constraints", {
        "max_adjustment_per_athlete_pct": int(ESCALATED_MAX_DELTA * 100),
        "source_age_limit_years": RESEARCH_WINDOW_YEARS,
        "prefer_latest_sources": True,
        "normalization_rule": "sum_to_one"
    })

    # Probabilities
    ap = ai_review["adjusted_probabilities"]
    ap.setdefault("before", {a1_name: before_a, a2_name: before_b})
    ap.setdefault("deltas", {a1_name: 0.0, a2_name: 0.0})
    ap.setdefault("after", {a1_name: before_a, a2_name: before_b})
    ap.setdefault("cap_applied", False)
    ap.setdefault("confidence_tier", "medium")
    ap.setdefault("reason", "")

    _ensure_names_in_probs(ap, a1_name, a2_name, before_a, before_b)
    # Determine cap from the model's constraints (default 30, allow 60 when justified)
    cap_pct = int(ai_review.get("constraints", {}).get("max_adjustment_per_athlete_pct", int(BASE_MAX_DELTA * 100)))
    # never exceed our hard ceiling
    cap = BASE_MAX_DELTA if cap_pct <= 30 else min(ESCALATED_MAX_DELTA, cap_pct / 100.0)

    d1 = _clamp(float(ap["deltas"].get(a1_name, 0.0)), -cap, cap)
    d2 = _clamp(float(ap["deltas"].get(a2_name, 0.0)), -cap, cap)
    # Optional nudge: if both deltas are zero but we have non-neutral, credible findings, apply a minimal tilt (±0.02)
    if abs(d1) < 1e-9 and abs(d2) < 1e-9:
        non_neutral = [f for f in ai_review.get("findings", []) if f.get("impact", {}).get("direction") in ("increase","decrease")]
        credible = []
        for f in non_neutral:
            ev = f.get("evidence") or []
            # at least one fresh, valid citation
            if any(_evidence_is_fresh(e, start_date, end_date) for e in ev):
                credible.append(f)
        if credible:
            # pick the strongest by magnitude, default 2%
            best = max(credible, key=lambda fx: int(fx.get("impact", {}).get("magnitude_pct", 0)))
            who = best.get("impact", {}).get("athlete_name")
            direction = best.get("impact", {}).get("direction")
            tilt = min(0.02, cap)  # 2 percentage points, respect cap
            if who == a1_name:
                d1 = tilt if direction == "increase" else -tilt
                d2 = -d1
            elif who == a2_name:
                d2 = tilt if direction == "increase" else -tilt
                d1 = -d2

    after_a = max(before_a + d1, 0.0)
    after_b = max(before_b + d2, 0.0)
    na, nb = _normalize_probs(after_a, after_b)

    ap["deltas"][a1_name] = round(d1, 3)
    ap["deltas"][a2_name] = round(d2, 3)
    ap["after"][a1_name] = round(na, 3)
    ap["after"][a2_name] = round(nb, 3)
    ap["before"][a1_name] = round(before_a, 3)
    ap["before"][a2_name] = round(before_b, 3)

    if d1 == 0.0 and d2 == 0.0 and not ap.get("reason"):
        ap["reason"] = "No material, well-sourced findings within the 2-year window; baseline retained."

    # Summary & narrative bounds
    if not isinstance(ai_review["summary"], list):
        ai_review["summary"] = [str(ai_review["summary"])]
    ai_review["summary"] = ai_review["summary"][:SUMMARY_MAX_BULLETS]
    # If fewer than desired bullets and we have findings, add titles as bullets (safe enrichment)
    while len(ai_review["summary"]) < SUMMARY_MIN_BULLETS and ai_review["findings"]:
        for f in ai_review["findings"]:
            if len(ai_review["summary"]) >= SUMMARY_MIN_BULLETS:
                break
            title = f.get("title")
            if title and title not in ai_review["summary"]:
                ai_review["summary"].append(title)

    # Findings: ensure objects + fresh evidence
    cleaned_findings: List[Dict[str, Any]] = []
    if isinstance(ai_review["findings"], list):
        for idx, f in enumerate(ai_review["findings"], start=1):
            if not isinstance(f, dict):
                # Convert stray strings into a minimal note finding
                f = {"id": f"FX{idx}", "type": "note", "title": str(f), "detail": str(f), "impact": {
                    "athlete_name": a1_name, "direction": "neutral", "magnitude_pct": 0, "confidence": "low"
                }, "evidence": []}

            f.setdefault("id", f"F{idx}")
            f.setdefault("type", "note")
            f.setdefault("title", f.get("detail", "Update"))
            f.setdefault("detail", f.get("title", "Update"))
            f.setdefault("impact", {"athlete_name": a1_name, "direction": "neutral", "magnitude_pct": 0, "confidence": "low"})
            f.setdefault("evidence", [])

            # Filter/keep only fresh evidence
            if isinstance(f["evidence"], list):
                f["evidence"] = [e for e in f["evidence"] if _evidence_is_fresh(e, start_date, end_date)]
            else:
                f["evidence"] = []

            cleaned_findings.append(f)
    ai_review["findings"] = cleaned_findings

    # UI highlights: ensure at least one badge/card if any finding has evidence
    _populate_min_ui(ai_review["ui_highlights"], ai_review["findings"])

    # Reproducibility (fill if missing)
    if "reproducibility" not in ai_review:
        ai_review["reproducibility"] = {
            "model": DEEPSEEK_MODEL,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "frequency_penalty": FREQ_PENALTY,
            "presence_penalty": PRES_PENALTY,
            "response_format": "json",
            "prompt_version": "ai_review:v1.3",
            "run_id": _now_iso(),
        }

    return {"ai_review": ai_review}


def _needs_retry(cleaned: Dict[str, Any]) -> bool:
    """Retry if no structured findings or all evidence is invalid/stale."""
    ai = cleaned.get("ai_review", {})
    findings = ai.get("findings", [])
    if not isinstance(findings, list) or len(findings) == 0:
        return True
    # Require at least one piece of fresh, valid evidence overall
    for f in findings:
        ev_list = f.get("evidence") or []
        for ev in ev_list:
            if _evidence_is_valid(ev):
                return False
    return True

# ---------- Public API ----------

def clarify_prediction_with_ai(
    athlete1_name: str,
    athlete2_name: str,
    match_arm: str = "Right",
    event_country: Optional[str] = None,
    event_title: Optional[str] = None,
    event_date: Optional[str] = None,
    timeout: int = 60,
    save: bool = False,   # still default: DO NOT write
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Generate base prediction, call DeepSeek for ai_review, return ONLY the ai_review by default.
    Silences base predictor logs so stdout is clean for API usage.
    """
    # Lazy import base predictor and silence import-time prints
    import importlib
    buf_import_out, buf_import_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_import_out), redirect_stderr(buf_import_err):
        up = importlib.import_module("universal_prediction")  # type: ignore
    universal_predict_and_save = getattr(up, "universal_predict_and_save")

    if verbose:
        print(f"[1/5] Generating base prediction for {athlete1_name} vs {athlete2_name} ({match_arm})")

    # Silence base predictor prints
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        base_result = universal_predict_and_save(
            athlete1_name, athlete2_name,
            match_arm=match_arm,
            event_country=event_country or "United States",
            event_title=event_title or "(Virtual)",
            event_date=event_date,
            verbose=False  # force quiet inside
        )
    if verbose:
        base_logs = buf_out.getvalue().strip()
        if base_logs:
            print("[base predictor logs suppressed]")
    del buf_out, buf_err

    if verbose:
        print("[2/5] Building DeepSeek prompt")

    # First attempt
    start_date, end_date = _two_year_window()
    system_prompt, user_prompt, meta = _build_prompts(base_result, strict_retry=False)

    if verbose:
        print("[3/5] Calling DeepSeek (attempt 1)")

    ai_json = _call_deepseek(system_prompt, user_prompt, timeout=timeout)
    cleaned = _postprocess_and_validate(
        ai_json,
        a1_name=meta["a1_name"],
        a2_name=meta["a2_name"],
        before_a=meta["before_a"],
        before_b=meta["before_b"],
        start_date=start_date,
        end_date=end_date,
    )

    

    # Retry once if structure/evidence is insufficient
    if _needs_retry(cleaned):
        if verbose:
            print("[3b/5] Retrying with stricter prompt (attempt 2)")
        system_prompt2, user_prompt2, _ = _build_prompts(base_result, strict_retry=True)
        ai_json2 = _call_deepseek(system_prompt2, user_prompt2, timeout=timeout)
        cleaned = _postprocess_and_validate(
            ai_json2,
            a1_name=meta["a1_name"],
            a2_name=meta["a2_name"],
            before_a=meta["before_a"],
            before_b=meta["before_b"],
            start_date=start_date,
            end_date=end_date,
        )

    if verbose:
        print("[4/5] Finalizing ai_review")

    # Optional save merged file (off by default)
    if save:
        try:
            from pipeline.config import TEMPORARY_PREDICTION_FOLDER  # type: ignore
            out_path = Path(TEMPORARY_PREDICTION_FOLDER) / f"{athlete1_name}_vs_{athlete2_name}_prediction.json"
            merged = dict(base_result)
            merged.update(cleaned)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            if verbose:
                print(f"✅ Saved merged prediction to: {out_path}")
        except Exception as e:
            raise RuntimeError("Failed to save merged JSON; check TEMPORARY_PREDICTION_FOLDER.") from e

    if verbose:
        print("[5/5] Done.")
    return cleaned


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Clarify a universal prediction with DeepSeek (returns ai_review only).")
    parser.add_argument("athlete1", help="First athlete name (left side).")
    parser.add_argument("athlete2", help="Second athlete name (right side).")
    parser.add_argument("--arm", default="Right", choices=["Right", "Left"], help="Match arm.")
    parser.add_argument("--country", default=None, help="Event country override.")
    parser.add_argument("--title", default=None, help="Event title override.")
    parser.add_argument("--date", default=None, help="Event date (YYYY-MM-DD).")
    parser.add_argument("--timeout", type=int, default=60, help="DeepSeek HTTP timeout seconds.")
    parser.add_argument("--save", action="store_true", help="Also write merged JSON back to file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    args = parser.parse_args()

    result = clarify_prediction_with_ai(
        args.athlete1,
        args.athlete2,
        match_arm=args.arm,
        event_country=args.country,
        event_title=args.title,
        event_date=args.date,
        timeout=args.timeout,
        save=args.save,
        verbose=args.verbose,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

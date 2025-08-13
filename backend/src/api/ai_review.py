# backend/src/api/ai_review.py
from __future__ import annotations

from flask_restx import Namespace, Resource, fields
from flask import request
from pathlib import Path
from datetime import datetime
import importlib
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

ns = Namespace(
    "ai-review",
    description="DeepSeek internet research that clarifies a universal prediction (returns only ai_review)."
)

# ---------- Locate and import ai_clarifier.py lazily ----------
def find_ai_clarifier_directory() -> Path:
    """
    Find the folder that contains ai_clarifier.py.

    Priority:
      1) AI_CLARIFIER_PATH / AI_CLARIFIER_DIR env overrides
      2) Fixed candidate paths (similar to find_prediction_model_directory)
      3) Fallback: shallow recursive search (rglob) under likely roots
    """
    import os
    current = Path(__file__).resolve()

    # --- 1) Env overrides ---
    env_path = os.getenv("AI_CLARIFIER_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file() and p.name == "ai_clarifier.py":
            return p.parent
        if (p / "ai_clarifier.py").is_file():
            return p
    env_dir = os.getenv("AI_CLARIFIER_DIR")
    if env_dir:
        d = Path(env_dir)
        if (d / "ai_clarifier.py").is_file():
            return d

    # --- 2) Fixed candidate paths (mirroring your prediction_model finder style) ---
    possible_paths = [
        # If you keep it next to prediction model code:
        current.parents[3] / "pipeline" / "prediction_model",
        current.parents[2] / "pipeline" / "prediction_model",
        current.parents[1] / "pipeline" / "prediction_model",
        Path.cwd() / "pipeline" / "prediction_model",
        Path.cwd().parent / "pipeline" / "prediction_model",

        # Common alternates:
        current.parents[3],
        current.parents[2],
        current.parents[1],
        Path.cwd(),
        Path.cwd().parent,

        # If you placed it under pipeline/prediction or pipeline root:
        current.parents[3] / "pipeline",
        current.parents[2] / "pipeline",
        current.parents[1] / "pipeline",
        Path.cwd() / "pipeline",
        Path.cwd().parent / "pipeline",

        current.parents[3] / "pipeline" / "prediction",
        current.parents[2] / "pipeline" / "prediction",
        current.parents[1] / "pipeline" / "prediction",
        Path.cwd() / "pipeline" / "prediction",
        Path.cwd().parent / "pipeline" / "prediction",
    ]

    for base in possible_paths:
        try:
            if base and (base / "ai_clarifier.py").is_file():
                return base
        except Exception:
            # some parents[x] may not exist on shorter paths; ignore
            pass

    # --- 3) Fallback: shallow recursive search under likely roots ---
    search_roots = [
        current.parents[3] if len(current.parents) >= 4 else current.parent,
        current.parents[2] if len(current.parents) >= 3 else current.parent,
        current.parents[1] if len(current.parents) >= 2 else current.parent,
        Path.cwd(),
        Path.cwd().parent,
    ]
    for root in search_roots:
        try:
            match = next((p for p in root.rglob("ai_clarifier.py") if p.is_file()), None)
            if match:
                return match.parent
        except Exception:
            continue

    raise FileNotFoundError(
        "Could not locate ai_clarifier.py. "
        "Set AI_CLARIFIER_PATH/AI_CLARIFIER_DIR or adjust find_ai_clarifier_directory() search paths."
    )

def import_ai_clarifier():
    """
    Lazily import ai_clarifier and return clarify_prediction_with_ai.
    Silences import-time prints to keep API responses clean.
    """
    clarifier_dir = find_ai_clarifier_directory()
    if str(clarifier_dir) not in sys.path:
        sys.path.insert(0, str(clarifier_dir))

    buf_out, buf_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        module = importlib.import_module("ai_clarifier")
    return getattr(module, "clarify_prediction_with_ai")

# ---------- Swagger models ----------
ai_review_request = ns.model("AIReviewRequest", {
    "athlete1_name": fields.String(example="Vitaly Laletin",required=True, description="First athlete name"),
    "athlete2_name": fields.String(example="Artyom Morozov",required=True, description="Second athlete name"),
    "match_arm": fields.String(example="Right",description="Left or Right arm (default: Right)"),
    "event_country": fields.String(description="Event country (default: United States)"),
    "event_title": fields.String(description="Event title (default: (Virtual))"),
    "event_date": fields.String(example="2025-08-13",description="Event date (YYYY-MM-DD, default: today)"),
    "timeout": fields.Integer(description="DeepSeek HTTP timeout seconds (default: 60)"),
    "verbose": fields.Boolean(description="Verbose server logs (default: false)")
})

# We keep the response simple for docs while returning the full ai_review structure.
ai_review_response = ns.model("AIReviewResponse", {
    "ai_review": fields.Raw(description="DeepSeek 'ai_review' research block with adjusted_probabilities, findings, ui_highlights, etc.")
})

# ---------- Endpoint ----------
@ns.route("/")
class AIReview(Resource):
    @ns.doc(description="Clarify a universal prediction using DeepSeek research. Returns only {'ai_review': {...}}.")
    @ns.expect(ai_review_request, validate=True)
    @ns.marshal_with(ai_review_response, code=200)
    def post(self):
        data = request.json or {}

        athlete1_name = (data.get("athlete1_name") or "").strip()
        athlete2_name = (data.get("athlete2_name") or "").strip()
        match_arm = (data.get("match_arm") or "Right").strip()
        event_country = (data.get("event_country") or "United States").strip()
        event_title = (data.get("event_title") or "(Virtual)").strip()
        event_date = data.get("event_date")
        timeout = int(data.get("timeout") or 60)
        verbose = bool(data.get("verbose") or False)

        # Basic validation
        if not athlete1_name or not athlete2_name:
            ns.abort(400, "athlete1_name and athlete2_name are required")

        if match_arm not in ["Left", "Right"]:
            ns.abort(400, "match_arm must be 'Left' or 'Right'")

        if event_date:
            try:
                datetime.strptime(event_date, "%Y-%m-%d")
            except ValueError:
                ns.abort(400, "event_date must be in YYYY-MM-DD format")

        try:
            clarify_prediction_with_ai = import_ai_clarifier()
            # Call with save=False to avoid file writes; returns {"ai_review": {...}}
            result = clarify_prediction_with_ai(
                athlete1_name=athlete1_name,
                athlete2_name=athlete2_name,
                match_arm=match_arm,
                event_country=event_country,
                event_title=event_title,
                event_date=event_date,
                timeout=timeout,
                save=False,
                verbose=verbose
            )
            # Marshal_with expects the shape declared; we already return {"ai_review": {...}}
            return result, 200

        except FileNotFoundError as e:
            ns.abort(500, f"ai_clarifier.py not found: {e}")
        except Exception as e:
            ns.abort(500, f"Error generating AI review: {str(e)}")


@ns.route("/test")
class AIReviewTest(Resource):
    @ns.doc(description="Quick test to verify ai_clarifier import works.")
    def get(self):
        try:
            import_ai_clarifier()
            return {"status": "ok", "ai_clarifier_import": True}, 200
        except Exception as e:
            ns.abort(500, f"Import failed: {e}")

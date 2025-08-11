# backend/src/api/prediction.py
from flask_restx import Namespace, Resource, fields
from flask import request
import sys
from pathlib import Path
import importlib.util

ns = Namespace("predict", description="Prediction endpoints")

# --- Correct path setup ---
API_DIR = Path(__file__).resolve().parent                 # .../backend/src/api
BACKEND_DIR = API_DIR.parents[1]                          # .../backend/src
BACKEND_ROOT = API_DIR.parents[1]                         # .../backend/src  (kept for reference)
PROJECT_ROOT = API_DIR.parents[2]                         # .../armwrestling_ai_project  <-- this is the one we want
PIPELINE_DIR = PROJECT_ROOT / "pipeline"

proj = str(PROJECT_ROOT)
if proj not in sys.path:
    sys.path.insert(0, proj)  # parent of 'pipeline' and 'backend'

# --- Import predictor robustly ---
universal_predict_and_save = None
import_error = None

try:
    from pipeline.prediction_model.universal_prediction import universal_predict_and_save  # type: ignore
except Exception as e1:
    import_error = e1
    # Fallback: load by file path
    candidate = PIPELINE_DIR / "prediction_model" / "universal_prediction.py"
    if candidate.exists():
        spec = importlib.util.spec_from_file_location("pipeline.prediction_model.universal_prediction", candidate)
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore
        universal_predict_and_save = getattr(mod, "universal_predict_and_save", None)

# ====== REQUEST MODEL ======
input_model = ns.model("PredictionInput", {
    "athlete1": fields.String(required=True),
    "athlete2": fields.String(required=True),
    "match_arm": fields.String(required=False, enum=["Right", "Left"], default="Right"),
    "event_country": fields.String(required=False, default="United States"),
    "event_title": fields.String(required=False, default="(Virtual)"),
    "event_date": fields.String(required=False, description="YYYY-MM-DD", default="2025-08-08"),
})

# ====== RESPONSE MODEL (rich) ======
result_model = ns.model("PredictionResult", {
    "prediction": fields.Raw,
    "match_details": fields.Raw,
    "athlete_profiles": fields.Raw,
    "analysis": fields.Raw,
    "valuable_matches": fields.Raw,
    "raw_features": fields.Raw,
    "metadata": fields.Raw,
})

@ns.route("/")
class Prediction(Resource):
    @ns.expect(input_model, validate=True)
    @ns.marshal_with(result_model, code=200)
    def post(self):
        if universal_predict_and_save is None:
            ns.abort(500, {
                "message": "Prediction engine unavailable",
                "project_root": str(PROJECT_ROOT),
                "pipeline_dir": str(PIPELINE_DIR),
                "sys_path_head": sys.path[:5],
                "import_error": str(import_error),
            })

        data = request.get_json(force=True) or {}
        result = universal_predict_and_save(
            athlete1_name=data["athlete1"],
            athlete2_name=data["athlete2"],
            match_arm=data.get("match_arm", "Right"),
            event_country=data.get("event_country", "United States"),
            event_title=data.get("event_title", "(Virtual)"),
            event_date=data.get("event_date", "2025-08-08"),
        )
        return result, 200

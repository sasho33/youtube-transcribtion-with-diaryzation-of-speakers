# backend/src/api/predict_match.py
from flask import request
from flask_restx import Namespace, Resource, fields
import sys
from pathlib import Path
import importlib.util

ns = Namespace("predict-match", description="Predict match outcome & odds")

# --- Path setup like prediction.py ---
API_DIR = Path(__file__).resolve().parent                 # .../backend/src/api
PROJECT_ROOT = API_DIR.parents[2]                         # .../<project root>
PIPELINE_DIR = PROJECT_ROOT / "pipeline"

proj = str(PROJECT_ROOT)
if proj not in sys.path:
    sys.path.insert(0, proj)  # allows "pipeline" import

predict_and_get_odds = None
import_error = None

try:
    from pipeline.prediction_model.predict_match import predict_and_get_odds  # type: ignore
except Exception as e1:
    import_error = e1
    # Fallback: load by file path
    candidate = PIPELINE_DIR / "prediction_model" / "predict_match.py"
    if candidate.exists():
        spec = importlib.util.spec_from_file_location("pipeline.prediction_model.predict_match", candidate)
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore
        predict_and_get_odds = getattr(mod, "predict_and_get_odds", None)

# ====== REQUEST MODEL ======
request_model = ns.model("PredictMatchRequest", {
    "event_title": fields.String(required=True, example="East vs West 18"),
    "athlete1": fields.String(required=True, example="Riekerd Bornman"),
    "athlete2": fields.String(required=True, example="Wallace Dilley"),
    "margin": fields.Float(required=False, default=0.85),
    "min_odds": fields.Float(required=False, default=1.1),
    "max_odds": fields.Float(required=False, default=10.0),
})

# ====== RESPONSE MODEL ======
response_model = ns.model("PredictMatchResponse", {
    "athlete1": fields.String,
    "athlete2": fields.String,
    "prob1_raw": fields.Float,
    "prob2_raw": fields.Float,
    "prob1_normalized": fields.Float,
    "prob2_normalized": fields.Float,
    "odds1": fields.Float,
    "odds2": fields.Float,
})

@ns.route("")
class PredictMatch(Resource):
    @ns.expect(request_model, validate=True)
    @ns.marshal_with(response_model, code=200)
    def post(self):
        if predict_and_get_odds is None:
            ns.abort(500, {
                "message": "Prediction engine unavailable",
                "project_root": str(PROJECT_ROOT),
                "pipeline_dir": str(PIPELINE_DIR),
                "sys_path_head": sys.path[:5],
                "import_error": str(import_error),
            })

        data = request.get_json(force=True) or {}
        res = predict_and_get_odds(
            event_title=data["event_title"],
            athlete1=data["athlete1"],
            athlete2=data["athlete2"],
            margin=data.get("margin", 0.85),
            min_odds=data.get("min_odds", 1.1),
            max_odds=data.get("max_odds", 10.0),
            print_console=False,
        )
        if res is None:
            ns.abort(
                404,
                f"No data found for match: {data['event_title']}, "
                f"{data['athlete1']} vs {data['athlete2']}"
            )
        return res, 200

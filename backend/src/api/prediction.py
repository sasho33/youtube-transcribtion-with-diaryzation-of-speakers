from flask_restx import Namespace, Resource, fields
from flask import request
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]  # project root
if str(root) not in sys.path:
    sys.path.append(str(root))

from pipeline.prediction_model.universal_prediction import universal_predict_and_save_json


ns = Namespace("predict", description="Prediction endpoints")

result_model = ns.model("PredictionResult", {
    "probability": fields.Float,
    "csv_saved_at": fields.String
})

@ns.route("/")
class Prediction(Resource):
    @ns.expect(ns.model("PredictionInput", {
        "athlete1": fields.String(required=True),
        "athlete2": fields.String(required=True),
        "match_arm": fields.String(default="Right"),
        "event_country": fields.String(default="United States"),
        "event_title": fields.String(default="(Virtual)"),
        "event_date": fields.String(default=None, description="YYYY-MM-DD or null"),
    }), validate=True)
    @ns.marshal_with(result_model)
    def post(self):
        data = request.json
        result = universal_predict_and_save_json(
            athlete1_name=data["athlete1"],
            athlete2_name=data["athlete2"],
            match_arm=data.get("match_arm", "Right"),
            event_country=data.get("event_country", "United States"),
            event_title=data.get("event_title", "(Virtual)"),
            event_date=data.get("event_date")
        )
        return result

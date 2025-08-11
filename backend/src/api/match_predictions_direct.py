# backend/src/api/match_predictions_direct.py
from flask_restx import Namespace, Resource, fields
from flask import request
import sys
import os
from pathlib import Path
from datetime import datetime

# Direct path resolution - find the pipeline directory
def find_pipeline_directory():
    """Find the pipeline directory from various possible locations."""
    current = Path(__file__).resolve()
    
    # Possible locations relative to this file
    possible_paths = [
        current.parents[3] / "pipeline",  # backend/src/api -> project/pipeline
        current.parents[2] / "pipeline",  # Different structure
        current.parents[1] / "pipeline",  # Another possibility
        Path.cwd() / "pipeline",          # From working directory
        Path.cwd().parent / "pipeline",   # One level up from working directory
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "find_prediction.py").exists():
            return path
    
    raise FileNotFoundError("Could not locate pipeline directory with find_prediction.py")

# Add pipeline to path
try:
    pipeline_dir = find_pipeline_directory()
    sys.path.insert(0, str(pipeline_dir))
    from find_prediction import get_prediction_arrays
    print(f"✅ Successfully imported from: {pipeline_dir}")
except Exception as e:
    print(f"❌ Import error: {e}")
    # Create a dummy function to prevent crashes
    def get_prediction_arrays(athlete1, athlete2, event_name, base_dir=None):
        return {
            "match": [athlete1, athlete2],
            "event": event_name,
            "self_predictions": [],
            "third_party_predictions": [],
            "match_found": False,
            "files_processed": [],
            "summary": {"total_predictions": 0, "error": f"Import failed: {e}"},
            "metadata": {"error": str(e)}
        }

ns = Namespace("match-predictions-direct", description="Direct match predictions (simplified)")

# Simple response model
response_model = ns.model("DirectPredictionResponse", {
    "match": fields.List(fields.String),
    "event": fields.String,
    "match_found": fields.Boolean,
    "self_predictions": fields.Raw,
    "third_party_predictions": fields.Raw,
    "summary": fields.Raw,
    "metadata": fields.Raw
})

@ns.route("/")
class DirectMatchPredictions(Resource):
    @ns.doc(description="Direct match prediction search")
    @ns.marshal_with(response_model)
    def post(self):
        """Direct prediction search without service layer."""
        data = request.json or {}
        
        athlete1 = data.get("athlete1", "").strip()
        athlete2 = data.get("athlete2", "").strip()
        event_name = data.get("event_name", "").strip()
        
        if not athlete1 or not athlete2 or not event_name:
            ns.abort(400, "athlete1, athlete2, and event_name are required")
        
        try:
            # Call the function directly
            result = get_prediction_arrays(athlete1, athlete2, event_name)
            
            # Add timestamp
            if "metadata" in result and isinstance(result["metadata"], dict):
                result["metadata"]["processed_at"] = datetime.utcnow().isoformat() + "Z"
                result["metadata"]["api_method"] = "direct"
            
            return result, 200
            
        except Exception as e:
            return {
                "match": [athlete1, athlete2],
                "event": event_name,
                "self_predictions": [],
                "third_party_predictions": [],
                "match_found": False,
                "files_processed": [],
                "summary": {"total_predictions": 0, "error": str(e)},
                "metadata": {"error": str(e), "processed_at": datetime.utcnow().isoformat() + "Z"}
            }, 500

    def options(self):
        """Handle OPTIONS preflight request."""
        return {}, 200

@ns.route("/test")
class TestEndpoint(Resource):
    def get(self):
        """Test endpoint to verify import and basic functionality."""
        try:
            # Test the import
            result = get_prediction_arrays("Devon Larratt", "Alex Kurdecha", "East vs West 18")
            return {
                "status": "success",
                "import_working": True,
                "match_found": result.get("match_found", False),
                "predictions_found": result.get("summary", {}).get("total_predictions", 0),
                "files_processed": len(result.get("files_processed", [])),
                "pipeline_dir": str(pipeline_dir) if 'pipeline_dir' in globals() else "unknown"
            }, 200
        except Exception as e:
            return {
                "status": "error",
                "import_working": False,
                "error": str(e),
                "pipeline_dir": str(pipeline_dir) if 'pipeline_dir' in globals() else "unknown"
            }, 500
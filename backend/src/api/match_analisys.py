# backend/src/api/match_analysis.py
from flask_restx import Namespace, Resource, fields
from flask import request
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the enhanced prediction module to path
def find_prediction_model_directory():
    """Find the prediction model directory"""
    current = Path(__file__).resolve()
    
    possible_paths = [
        current.parents[3] / "pipeline" / "prediction_model",
        current.parents[2] / "pipeline" / "prediction_model", 
        current.parents[1] / "pipeline" / "prediction_model",
        Path.cwd() / "pipeline" / "prediction_model",
        Path.cwd().parent / "pipeline" / "prediction_model",
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "enhanced_universal_prediction.py").exists():
            return path
    
    raise FileNotFoundError("Could not locate enhanced_universal_prediction.py")

try:
    prediction_dir = find_prediction_model_directory()
    sys.path.insert(0, str(prediction_dir))
    from enhanced_universal_prediction import enhanced_universal_predict
    print(f"✅ Successfully imported enhanced prediction from: {prediction_dir}")
except Exception as e:
    print(f"❌ Import error: {e}")
    # Create a dummy function to prevent crashes
    def enhanced_universal_predict(athlete1_name, athlete2_name, **kwargs):
        return {
            "prediction": {
                "athlete1_name": athlete1_name,
                "athlete2_name": athlete2_name,
                "athlete1_win_probability": 0.5,
                "athlete2_win_probability": 0.5,
                "confidence": "Low"
            },
            "error": f"Enhanced prediction not available: {e}"
        }

ns = Namespace("match-analysis", description="Enhanced match analysis with detailed predictions")

# Response models for Swagger documentation
athlete_profile_model = ns.model("AthleteProfile", {
    "name": fields.String(description="Athlete name"),
    "age": fields.Integer(description="Age in years"),
    "weight_kg": fields.Float(description="Weight in kilograms"),
    "height_cm": fields.Float(description="Height in centimeters"),
    "country": fields.String(description="Country of origin"),
    "dominant_style": fields.String(description="Primary pulling style"),
    "additional_style": fields.String(description="Secondary pulling style"),
    "is_title_holder": fields.Boolean(description="Current title holder status"),
    "current_winning_streak": fields.Integer(description="Current winning streak"),
    "domestic_win_rate": fields.Float(description="Win rate in domestic competitions"),
    "transatlantic_win_rate": fields.Float(description="Win rate in international competitions")
})

explanation_model = ns.model("Explanation", {
    "category": fields.String(description="Category of the factor (Physical, Experience, etc.)"),
    "title": fields.String(description="Title of the explanation"),
    "description": fields.String(description="Human-readable explanation"),
    "impact": fields.String(description="Impact type: positive, negative, or neutral"),
    "value": fields.Float(description="Numeric value of the factor")
})

match_model = ns.model("Match", {
    "event": fields.String(description="Event name"),
    "participants": fields.List(fields.String, description="Match participants"),
    "date": fields.String(description="Match date"),
    "arm": fields.String(description="Left or Right arm"),
    "winner": fields.String(description="Match winner"),
    "result": fields.String(description="Result type"),
    "score": fields.String(description="Match score")
})

shared_opponent_model = ns.model("SharedOpponent", {
    "shared_opponent": fields.String(description="Name of shared opponent"),
    "matches": fields.List(fields.Nested(match_model), description="Matches against this opponent")
})

key_factors_model = ns.model("KeyFactors", {
    "weight_advantage_kg": fields.Float(description="Weight advantage in kilograms"),
    "height_advantage_cm": fields.Float(description="Height advantage in centimeters"),
    "age_difference": fields.Integer(description="Age difference in years"),
    "travel_advantage": fields.Float(description="Travel/domestic advantage score"),
    "style_advantage_rate": fields.Float(description="Style matchup advantage percentage"),
    "has_head_to_head_history": fields.Boolean(description="Whether athletes have faced each other"),
    "shared_opponents_count": fields.Integer(description="Number of shared opponents"),
    "mma_math_advantage": fields.Integer(description="MMA math advantage score")
})

prediction_model = ns.model("Prediction", {
    "athlete1_name": fields.String(description="First athlete name"),
    "athlete2_name": fields.String(description="Second athlete name"),
    "athlete1_win_probability": fields.Float(description="Probability of athlete1 winning (0-1)"),
    "athlete2_win_probability": fields.Float(description="Probability of athlete2 winning (0-1)"),
    "confidence": fields.String(description="Prediction confidence level")
})

analysis_model = ns.model("Analysis", {
    "explanations": fields.List(fields.Nested(explanation_model), description="Human-readable explanations"),
    "key_factors": fields.Nested(key_factors_model, description="Key numerical factors")
})

valuable_matches_model = ns.model("ValuableMatches", {
    "head_to_head": fields.List(fields.Nested(match_model), description="Direct head-to-head matches"),
    "shared_opponents": fields.List(fields.Nested(shared_opponent_model), description="Matches against shared opponents"),
    "second_order_connections": fields.Raw(description="Second-order opponent connections")
})

match_analysis_response_model = ns.model("MatchAnalysisResponse", {
    "prediction": fields.Nested(prediction_model, description="Win probability prediction"),
    "match_details": fields.Raw(description="Match event details"),
    "athlete_profiles": fields.Raw(description="Detailed athlete profiles"),
    "analysis": fields.Nested(analysis_model, description="Detailed analysis and explanations"),
    "valuable_matches": fields.Nested(valuable_matches_model, description="Historical match data"),
    "raw_features": fields.Raw(description="Raw model features for debugging"),
    "metadata": fields.Raw(description="Prediction metadata")
})

# Input model
match_analysis_input_model = ns.model("MatchAnalysisInput", {
    "athlete1_name": fields.String(required=True, description="Name of first athlete"),
    "athlete2_name": fields.String(required=True, description="Name of second athlete"),
    "match_arm": fields.String(description="Left or Right arm (default: Right)"),
    "event_country": fields.String(description="Event country (default: United States)"),
    "event_title": fields.String(description="Event title (default: Virtual)"),
    "event_date": fields.String(description="Event date in YYYY-MM-DD format (default: today)")
})

@ns.route("/")
class MatchAnalysis(Resource):
    @ns.doc(description="Get detailed match analysis and prediction")
    @ns.expect(match_analysis_input_model, validate=True)
    @ns.marshal_with(match_analysis_response_model)
    def post(self):
        """
        Generate detailed match analysis including win predictions, explanations, and historical data.
        
        This endpoint provides comprehensive analysis including:
        - Win probability predictions
        - Physical and technical advantages/disadvantages
        - Historical head-to-head data
        - Shared opponent comparisons
        - Detailed explanations for each factor
        """
        data = request.json or {}
        
        athlete1_name = data.get("athlete1_name", "").strip()
        athlete2_name = data.get("athlete2_name", "").strip()
        match_arm = data.get("match_arm", "Right")
        event_country = data.get("event_country", "United States")
        event_title = data.get("event_title", "(Virtual)")
        event_date = data.get("event_date")
        
        # Validate required inputs
        if not athlete1_name or not athlete2_name:
            ns.abort(400, "athlete1_name and athlete2_name are required")
        
        # Validate match arm
        if match_arm not in ["Left", "Right"]:
            ns.abort(400, "match_arm must be 'Left' or 'Right'")
        
        # Validate date format if provided
        if event_date:
            try:
                datetime.strptime(event_date, "%Y-%m-%d")
            except ValueError:
                ns.abort(400, "event_date must be in YYYY-MM-DD format")
        
        try:
            result = enhanced_universal_predict(
                athlete1_name=athlete1_name,
                athlete2_name=athlete2_name,
                match_arm=match_arm,
                event_country=event_country,
                event_title=event_title,
                event_date=event_date,
                verbose=False
            )
            
            return result, 200
            
        except Exception as e:
            ns.abort(500, f"Error generating match analysis: {str(e)}")

@ns.route("/quick")
class QuickMatchAnalysis(Resource):
    @ns.doc(description="Get quick match prediction without detailed analysis")
    @ns.doc(params={
        "athlete1": "Name of first athlete (required)",
        "athlete2": "Name of second athlete (required)",
        "arm": "Left or Right arm (default: Right)",
        "country": "Event country (default: United States)"
    })
    def get(self):
        """
        Get a quick win probability prediction without detailed analysis.
        
        Useful for lightweight requests when you only need the basic prediction.
        """
        athlete1_name = request.args.get("athlete1", "").strip()
        athlete2_name = request.args.get("athlete2", "").strip()
        match_arm = request.args.get("arm", "Right")
        event_country = request.args.get("country", "United States")
        
        if not athlete1_name or not athlete2_name:
            ns.abort(400, "athlete1 and athlete2 parameters are required")
        
        try:
            result = enhanced_universal_predict(
                athlete1_name=athlete1_name,
                athlete2_name=athlete2_name,
                match_arm=match_arm,
                event_country=event_country,
                verbose=False
            )
            
            # Return only the essential prediction data
            quick_result = {
                "athlete1_name": result["prediction"]["athlete1_name"],
                "athlete2_name": result["prediction"]["athlete2_name"],
                "athlete1_win_probability": result["prediction"]["athlete1_win_probability"],
                "athlete2_win_probability": result["prediction"]["athlete2_win_probability"],
                "confidence": result["prediction"]["confidence"],
                "key_advantages": [
                    exp for exp in result["analysis"]["explanations"] 
                    if exp["impact"] in ["positive", "negative"]
                ][:3]  # Top 3 advantages/disadvantages
            }
            
            return quick_result, 200
            
        except Exception as e:
            ns.abort(500, f"Error generating quick prediction: {str(e)}")

@ns.route("/compare")
class AthleteComparison(Resource):
    @ns.doc(description="Compare two athletes across multiple factors")
    @ns.doc(params={
        "athlete1": "Name of first athlete (required)",
        "athlete2": "Name of second athlete (required)"
    })
    def get(self):
        """
        Get a detailed comparison of two athletes across various factors.
        
        Returns side-by-side comparison without event-specific context.
        """
        athlete1_name = request.args.get("athlete1", "").strip()
        athlete2_name = request.args.get("athlete2", "").strip()
        
        if not athlete1_name or not athlete2_name:
            ns.abort(400, "athlete1 and athlete2 parameters are required")
        
        try:
            result = enhanced_universal_predict(
                athlete1_name=athlete1_name,
                athlete2_name=athlete2_name,
                verbose=False
            )
            
            # Extract comparison data
            comparison = {
                "athletes": {
                    "athlete1": result["athlete_profiles"]["athlete1"],
                    "athlete2": result["athlete_profiles"]["athlete2"]
                },
                "physical_comparison": {
                    "weight_difference_kg": result["analysis"]["key_factors"]["weight_advantage_kg"],
                    "height_difference_cm": result["analysis"]["key_factors"]["height_advantage_cm"],
                    "age_difference": result["analysis"]["key_factors"]["age_difference"]
                },
                "performance_comparison": {
                    "style_advantage": result["analysis"]["key_factors"]["style_advantage_rate"],
                    "head_to_head_history": result["analysis"]["key_factors"]["has_head_to_head_history"],
                    "shared_opponents": result["analysis"]["key_factors"]["shared_opponents_count"]
                },
                "explanations": result["analysis"]["explanations"],
                "valuable_matches": result["valuable_matches"]
            }
            
            return comparison, 200
            
        except Exception as e:
            ns.abort(500, f"Error generating athlete comparison: {str(e)}")

@ns.route("/test")
class TestAnalysisEndpoint(Resource):
    def get(self):
        """Test endpoint to verify the enhanced prediction system is working."""
        try:
            # Test with known athletes
            result = enhanced_universal_predict(
                athlete1_name="Devon Larratt",
                athlete2_name="Kamil Jablonski",
                verbose=False
            )
            
            return {
                "status": "success",
                "system_working": True,
                "prediction_generated": True,
                "explanations_count": len(result["analysis"]["explanations"]),
                "shared_opponents_found": len(result["valuable_matches"]["shared_opponents"]),
                "sample_probability": result["prediction"]["athlete1_win_probability"]
            }, 200
            
        except Exception as e:
            return {
                "status": "error",
                "system_working": False,
                "error": str(e)
            }, 500
# backend/src/api/match_predictions.py
from flask_restx import Namespace, Resource, fields
from flask import request
from ..services.match_predictions_service import (
    get_match_predictions_with_metadata,
    validate_match_prediction_request,
    get_prediction_summary_only
)

ns = Namespace("match-predictions", description="Find predictions for specific matches")

# Define response models for Swagger documentation
athlete_opinion_model = ns.model("AthleteOpinion", {
    "strength": fields.String(description="Assessment of athlete's strength"),
    "health": fields.String(description="Assessment of athlete's health"),
    "previous_match_summary": fields.String(description="Summary of previous performance")
})

prediction_detail_model = ns.model("PredictionDetail", {
    "predictor": fields.String(description="Name of the person making the prediction"),
    "match": fields.List(fields.String, description="Match participants"),
    "arm": fields.String(description="Left or Right arm"),
    "event": fields.String(description="Event name"),
    "predicted_winner": fields.String(description="Predicted winner"),
    "predicted_score": fields.String(description="Predicted score (e.g., '3-2')"),
    "prediction_summary": fields.String(description="Detailed reasoning for the prediction"),
    "predicted_duration": fields.String(description="Expected match duration"),
    "style_conflict": fields.String(description="Description of style matchup"),
    "confidence": fields.String(description="Confidence level of prediction"),
    "reasoning": fields.String(description="Additional reasoning"),
    "opinion_about_athletes": fields.Raw(description="Opinions about each athlete")
})

summary_model = ns.model("PredictionSummary", {
    "total_predictions": fields.Integer(description="Total number of predictions found"),
    "self_count": fields.Integer(description="Number of self-predictions (from participants)"),
    "third_party_count": fields.Integer(description="Number of third-party predictions"),
    "vote_distribution": fields.Raw(description="Vote count for each athlete"),
    "consensus_favorite": fields.String(description="Athlete with most predictions"),
    "prediction_confidence": fields.Float(description="Confidence score (0-1)")
})

metadata_model = ns.model("PredictionMetadata", {
    "processed_at": fields.String(description="Processing timestamp"),
    "data_quality_score": fields.Float(description="Quality score based on detail level"),
    "unique_predictors": fields.Integer(description="Number of unique predictors"),
    "has_detailed_summaries": fields.Boolean(description="Whether detailed summaries exist"),
    "has_athlete_opinions": fields.Boolean(description="Whether athlete opinions exist")
})

match_predictions_response_model = ns.model("MatchPredictionsResponse", {
    "match": fields.List(fields.String, description="Match participants"),
    "event": fields.String(description="Event name"),
    "self_predictions": fields.List(fields.Nested(prediction_detail_model)),
    "third_party_predictions": fields.List(fields.Nested(prediction_detail_model)),
    "match_found": fields.Boolean(description="Whether predictions were found"),
    "files_processed": fields.List(fields.String, description="List of processed transcript files"),
    "summary": fields.Nested(summary_model),
    "metadata": fields.Nested(metadata_model)
})

# Input model for query parameters
match_predictions_input_model = ns.model("MatchPredictionsInput", {
    "athlete1": fields.String(required=True, description="Name of first athlete"),
    "athlete2": fields.String(required=True, description="Name of second athlete"),
    "event_name": fields.String(required=True, description="Name of the event (e.g., 'East vs West 5')")
})

@ns.route("/")
class MatchPredictions(Resource):
    @ns.doc(description="Find all predictions for a specific match")
    @ns.expect(match_predictions_input_model, validate=True)
    @ns.marshal_with(match_predictions_response_model)
    def post(self):
        """
        Find predictions for a specific match between two athletes in an event.
        
        Searches through transcript files to find all predictions made about the match,
        including self-predictions from the athletes and third-party predictions from experts.
        """
        data = request.json or {}
        
        athlete1 = data.get("athlete1", "").strip()
        athlete2 = data.get("athlete2", "").strip()
        event_name = data.get("event_name", "").strip()
        
        # Validate input
        errors = validate_match_prediction_request(athlete1, athlete2, event_name)
        if errors:
            ns.abort(400, f"Validation errors: {errors}")
        
        try:
            result = get_match_predictions_with_metadata(athlete1, athlete2, event_name)
            return result, 200
        except Exception as e:
            ns.abort(500, f"Error processing predictions: {str(e)}")

@ns.route("/search")
class MatchPredictionsSearch(Resource):
    @ns.doc(description="Find predictions using query parameters")
    @ns.doc(params={
        "athlete1": "Name of first athlete (required)",
        "athlete2": "Name of second athlete (required)", 
        "event_name": "Name of the event (required)"
    })
    @ns.marshal_with(match_predictions_response_model)
    def get(self):
        """
        Find predictions for a specific match using query parameters.
        
        Alternative endpoint that accepts parameters via URL query string.
        """
        athlete1 = request.args.get("athlete1", "").strip()
        athlete2 = request.args.get("athlete2", "").strip()
        event_name = request.args.get("event_name", "").strip()
        
        # Validate input
        errors = validate_match_prediction_request(athlete1, athlete2, event_name)
        if errors:
            ns.abort(400, f"Validation errors: {errors}")
        
        try:
            result = get_match_predictions_with_metadata(athlete1, athlete2, event_name)
            return result, 200
        except Exception as e:
            ns.abort(500, f"Error processing predictions: {str(e)}")

@ns.route("/summary")
class MatchPredictionsSummary(Resource):
    @ns.doc(description="Get only the summary data for a match")
    @ns.doc(params={
        "athlete1": "Name of first athlete (required)",
        "athlete2": "Name of second athlete (required)",
        "event_name": "Name of the event (required)"
    })
    def get(self):
        """
        Get only summary statistics for a match without detailed predictions.
        
        Useful for quick overview without loading full prediction details.
        """
        athlete1 = request.args.get("athlete1", "").strip()
        athlete2 = request.args.get("athlete2", "").strip() 
        event_name = request.args.get("event_name", "").strip()
        
        # Validate input
        errors = validate_match_prediction_request(athlete1, athlete2, event_name)
        if errors:
            ns.abort(400, f"Validation errors: {errors}")
        
        try:
            result = get_prediction_summary_only(athlete1, athlete2, event_name)
            return result, 200
        except Exception as e:
            ns.abort(500, f"Error processing predictions: {str(e)}")

@ns.route("/events/<path:event_name>/matches")
class EventMatches(Resource):
    @ns.doc(description="Get all available matches for a specific event")
    @ns.param("event_name", "Name of the event (URL encoded)")
    def get(self, event_name):
        """
        Get a list of all available matches for a specific event.
        
        This could be useful for discovering what matches have predictions available.
        Note: This is a placeholder - you'd need to implement match discovery logic.
        """
        # This would require scanning all transcript files for the event
        # and extracting unique match combinations
        # For now, return a placeholder response
        return {
            "event": event_name,
            "message": "Match discovery not yet implemented",
            "suggestion": "Use the main endpoint with specific athlete names"
        }, 501
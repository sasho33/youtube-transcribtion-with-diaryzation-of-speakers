# backend/src/services/match_predictions_service.py
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add pipeline directory to path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from pipeline.find_prediction import get_match_predictions as pipeline_get_match_predictions

def get_match_predictions_with_metadata(
    athlete1: str, 
    athlete2: str, 
    event_name: str,
    base_transcript_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhanced wrapper around the pipeline function that adds processing metadata.
    
    Args:
        athlete1: Name of first athlete
        athlete2: Name of second athlete
        event_name: Name of the event
        base_transcript_dir: Optional base transcript directory
    
    Returns:
        Enhanced result with processing timestamp and additional metadata
    """
    try:
        # Call the pipeline function
        result = pipeline_get_match_predictions(athlete1, athlete2, event_name, base_transcript_dir)
        
        # Add processing timestamp
        if result.get("metadata"):
            result["metadata"]["processed_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Add API-specific metadata
        result["api_version"] = "1.0"
        result["request_info"] = {
            "athlete1": athlete1,
            "athlete2": athlete2,
            "event_name": event_name
        }
        
        return result
        
    except Exception as e:
        # Return error in consistent format
        return {
            "match": [athlete1, athlete2],
            "event": event_name,
            "self_predictions": [],
            "third_party_predictions": [],
            "match_found": False,
            "files_processed": [],
            "summary": {
                "total_predictions": 0,
                "self_count": 0,
                "third_party_count": 0,
                "vote_distribution": {athlete1: 0, athlete2: 0},
                "consensus_favorite": None,
                "prediction_confidence": 0.0
            },
            "metadata": {
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "data_quality_score": 0.0,
                "unique_predictors": 0,
                "has_detailed_summaries": False,
                "has_athlete_opinions": False,
                "error": str(e)
            },
            "api_version": "1.0",
            "request_info": {
                "athlete1": athlete1,
                "athlete2": athlete2,
                "event_name": event_name
            }
        }

def validate_match_prediction_request(athlete1: str, athlete2: str, event_name: str) -> Dict[str, str]:
    """
    Validate match prediction request parameters.
    
    Returns:
        Dictionary with validation errors, empty if valid
    """
    errors = {}
    
    if not athlete1 or not athlete1.strip():
        errors["athlete1"] = "Athlete 1 name is required"
    
    if not athlete2 or not athlete2.strip():
        errors["athlete2"] = "Athlete 2 name is required"
        
    if not event_name or not event_name.strip():
        errors["event_name"] = "Event name is required"
        
    if athlete1 and athlete2 and athlete1.strip().lower() == athlete2.strip().lower():
        errors["athletes"] = "Athlete names must be different"
    
    return errors

def get_prediction_summary_only(athlete1: str, athlete2: str, event_name: str) -> Dict[str, Any]:
    """
    Get only summary data without full prediction details.
    
    Returns:
        Lightweight summary response
    """
    full_result = get_match_predictions_with_metadata(athlete1, athlete2, event_name)
    
    return {
        "match": full_result["match"],
        "event": full_result["event"],
        "match_found": full_result["match_found"],
        "summary": full_result["summary"],
        "metadata": full_result["metadata"],
        "api_version": full_result.get("api_version"),
        "request_info": full_result.get("request_info")
    }
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz
import sys

# Adjust import path for config if needed
try:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from pipeline.config import TRANSCRIPT_DIR, PREDICTIONS_DIR
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    TRANSCRIPT_DIR = Path("data/transcripts")
    PREDICTIONS_DIR = Path("data/predictions")

FUZZ_THRESHOLD = 85

def _fuzzy_match(name1: str, name2: str) -> bool:
    """Check if two names match using fuzzy string matching."""
    # Handle None values
    if name1 is None or name2 is None:
        return False
    
    # Convert to strings if not already
    name1_str = str(name1) if name1 is not None else ""
    name2_str = str(name2) if name2 is not None else ""
    
    # Skip empty strings
    if not name1_str.strip() or not name2_str.strip():
        return False
        
    return fuzz.ratio(name1_str.lower(), name2_str.lower()) >= FUZZ_THRESHOLD

def _is_match_participant(participant_name: str, athlete1: str, athlete2: str) -> bool:
    """Check if a participant name matches either of the target athletes using fuzzy matching."""
    return _fuzzy_match(participant_name, athlete1) or _fuzzy_match(participant_name, athlete2)

def _normalize_match_participants(match_participants: List[str], athlete1: str, athlete2: str) -> bool:
    """
    Check if the match participants correspond to the target athletes.
    Returns True if both target athletes are found in match_participants (in any order).
    """
    if len(match_participants) != 2:
        return False
    
    # Check if both target athletes are found in the match
    athlete1_found = any(_fuzzy_match(athlete1, participant) for participant in match_participants)
    athlete2_found = any(_fuzzy_match(athlete2, participant) for participant in match_participants)
    
    return athlete1_found and athlete2_found

def find_event_transcript_files(event_name: str, base_transcript_dir: str = None) -> List[Path]:
    """
    Find all transcript files for a specific event in the Identified folder structure.
    
    Args:
        event_name: Name of the event (e.g., "East vs West 5")
        base_transcript_dir: Base transcript directory path
    
    Returns:
        List of Path objects to transcript files
    """
    if base_transcript_dir is None:
        base_transcript_dir = TRANSCRIPT_DIR if USE_CONFIG else "data/transcripts"
    
    transcript_dir = Path(base_transcript_dir)
    
    # Look for event directory and Identified subfolder
    event_dir = transcript_dir / event_name / "Identified"
    
    transcript_files = []
    if event_dir.exists():
        # Find all JSON files in the Identified folder
        transcript_files = list(event_dir.glob("*.json"))
        print(f"📂 Found {len(transcript_files)} transcript files for {event_name}")
    else:
        print(f"⚠️ Event directory not found: {event_dir}")
        
        # Fallback: search for similar event names
        for potential_dir in transcript_dir.iterdir():
            if potential_dir.is_dir() and _fuzzy_match(potential_dir.name, event_name):
                identified_dir = potential_dir / "Identified"
                if identified_dir.exists():
                    transcript_files = list(identified_dir.glob("*.json"))
                    print(f"📂 Found similar event: {potential_dir.name}, {len(transcript_files)} files")
                    break
    
    return transcript_files

def flatten_predictions(transcript_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Flatten predictions from various transcript formats into a standardized structure.
    
    Args:
        transcript_data: The loaded transcript JSON data
    
    Returns:
        Dictionary mapping speaker names to their predictions
    """
    results = {}
    
    # Format 1: full 'predictions' structure with nested speaker data
    predictions_block = transcript_data.get("predictions", {})
    if isinstance(predictions_block, dict):
        for speaker, speaker_data in predictions_block.items():
            if isinstance(speaker_data, dict):
                results.setdefault(speaker, [])
                results[speaker].extend(speaker_data.get("self_predictions", []))
                results[speaker].extend(speaker_data.get("third_party_predictions", []))
    
    # Format 2: predictions as a list of blocks
    elif isinstance(predictions_block, list):
        for block in predictions_block:
            speaker = block.get("speaker")
            if speaker:
                results.setdefault(speaker, [])
                results[speaker].extend(block.get("self_predictions", []))
                results[speaker].extend(block.get("third_party_predictions", []))
    
    # Format 3: direct self_predictions and third_party_predictions dictionaries
    for pred_type in ["self_predictions", "third_party_predictions"]:
        block = transcript_data.get(pred_type)
        if isinstance(block, dict):
            for speaker, preds in block.items():
                results.setdefault(speaker, [])
                if isinstance(preds, list):
                    results[speaker].extend(preds)
    
    return results

def extract_match_predictions(athlete1: str, athlete2: str, event_name: str, base_transcript_dir: str = None) -> Dict[str, Any]:
    """
    Extract all predictions for a specific match from event transcript files.
    
    Args:
        athlete1: Name of first athlete
        athlete2: Name of second athlete
        event_name: Name of the event to search in
        base_transcript_dir: Base transcript directory path
    
    Returns:
        Dictionary containing self predictions and third party predictions
    """
    result = {
        "match": [athlete1, athlete2],
        "event": event_name,
        "self_predictions": [],
        "third_party_predictions": [],
        "match_found": False,
        "files_processed": []
    }
    
    # Find all transcript files for the event
    transcript_files = find_event_transcript_files(event_name, base_transcript_dir)
    
    if not transcript_files:
        print(f"❌ No transcript files found for event: {event_name}")
        return result
    
    # Process each transcript file
    for file_path in transcript_files:
        try:
            print(f"📄 Processing: {file_path.name}")
            file_result = _process_transcript_file(file_path, athlete1, athlete2, event_name)
            
            # Merge results
            result["self_predictions"].extend(file_result["self_predictions"])
            result["third_party_predictions"].extend(file_result["third_party_predictions"])
            result["files_processed"].append(str(file_path.name))
            
            if file_result["match_found"]:
                result["match_found"] = True
                
        except Exception as e:
            print(f"❌ Error processing file {file_path}: {e}")
            continue
    
    print(f"✅ Found {len(result['self_predictions'])} self predictions and {len(result['third_party_predictions'])} third party predictions")
    return result

def _process_transcript_file(file_path: Path, athlete1: str, athlete2: str, event_name: str) -> Dict[str, Any]:
    """Process a single transcript file and extract relevant predictions."""
    result = {
        "self_predictions": [],
        "third_party_predictions": [],
        "match_found": False
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        # Flatten predictions from various formats
        speaker_predictions = flatten_predictions(transcript_data)
        
        # Process predictions for each speaker
        for speaker_name, predictions in speaker_predictions.items():
            for prediction in predictions:
                if _process_single_prediction(prediction, athlete1, athlete2, event_name, speaker_name, result):
                    result["match_found"] = True
    
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
    
    return result

def _process_single_prediction(prediction: Dict[str, Any], athlete1: str, athlete2: str, event_name: str, 
                             predictor_name: str, result: Dict[str, Any]) -> bool:
    """Process a single prediction and add it to results if it matches the target."""
    match_participants = prediction.get("match", [])
    prediction_event = prediction.get("event", "")
    
    # Skip if essential data is missing
    if not match_participants or not prediction_event:
        return False
    
    # Additional safety check for predictor_name
    if predictor_name is None:
        predictor_name = "Unknown"
    
    # Check if this prediction is for our target match and event
    if (_normalize_match_participants(match_participants, athlete1, athlete2) and 
        _fuzzy_match(prediction_event, event_name)):
        
        # Create enhanced prediction object with safer data handling
        opinion_data = prediction.get("opinion_about_athletes")
        if not isinstance(opinion_data, dict):
            opinion_data = {}
            
        enhanced_prediction = {
            "predictor": str(predictor_name) if predictor_name else "Unknown",
            "match": prediction.get("match", []),
            "arm": str(prediction.get("arm", "")) if prediction.get("arm") else "",
            "event": str(prediction.get("event", "")) if prediction.get("event") else "",
            "predicted_winner": str(prediction.get("predicted_winner", "")) if prediction.get("predicted_winner") else "",
            "predicted_score": str(prediction.get("predicted_score", "")) if prediction.get("predicted_score") else "",
            "prediction_summary": str(prediction.get("prediction_summary", "")) if prediction.get("prediction_summary") else "",
            "predicted_duration": str(prediction.get("predicted_duration", "")) if prediction.get("predicted_duration") else "",
            "style_conflict": str(prediction.get("style_conflict", "")) if prediction.get("style_conflict") else "",
            "confidence": str(prediction.get("confidence", "")) if prediction.get("confidence") else "",
            "reasoning": str(prediction.get("reasoning", "")) if prediction.get("reasoning") else "",
            "opinion_about_athletes": opinion_data
        }
        
        # Determine if this is a self prediction (predictor is one of the athletes)
        is_self_prediction = (predictor_name and 
                             (_fuzzy_match(str(predictor_name), athlete1) or 
                              _fuzzy_match(str(predictor_name), athlete2)))
        
        # Add to appropriate category
        if is_self_prediction:
            result["self_predictions"].append(enhanced_prediction)
        else:
            result["third_party_predictions"].append(enhanced_prediction)
        
        return True
    
    return False

def get_prediction_summary(athlete1: str, athlete2: str, event_name: str, base_transcript_dir: str = None) -> Dict[str, Any]:
    """
    Get a summary of all predictions for a match, including vote counts and consensus.
    """
    predictions = extract_match_predictions(athlete1, athlete2, event_name, base_transcript_dir)
    
    if not predictions["match_found"]:
        return predictions
    
    # Analyze predictions
    summary = predictions.copy()
    
    # Count votes for each athlete
    athlete1_votes = 0
    athlete2_votes = 0
    total_predictions = len(predictions["self_predictions"]) + len(predictions["third_party_predictions"])
    
    all_predictions = predictions["self_predictions"] + predictions["third_party_predictions"]
    
    for pred in all_predictions:
        winner = pred.get("predicted_winner", "")
        if _fuzzy_match(winner, athlete1):
            athlete1_votes += 1
        elif _fuzzy_match(winner, athlete2):
            athlete2_votes += 1
    
    # Add summary statistics
    summary["prediction_summary"] = {
        "total_predictions": total_predictions,
        "self_predictions_count": len(predictions["self_predictions"]),
        "third_party_predictions_count": len(predictions["third_party_predictions"]),
        "vote_distribution": {
            athlete1: athlete1_votes,
            athlete2: athlete2_votes
        },
        "consensus_favorite": athlete1 if athlete1_votes > athlete2_votes else athlete2 if athlete2_votes > athlete1_votes else "No consensus",
        "prediction_confidence": max(athlete1_votes, athlete2_votes) / total_predictions if total_predictions > 0 else 0
    }
    
    return summary

# Main function to get all prediction data
def get_match_predictions(athlete1: str, athlete2: str, event_name: str, base_transcript_dir: str = None) -> Dict[str, Any]:
    """
    Main function to get all prediction data for a match.
    
    Args:
        athlete1: Name of first athlete
        athlete2: Name of second athlete  
        event_name: Name of the event
        base_transcript_dir: Base transcript directory path
    
    Returns:
        Complete dictionary with all prediction arrays and summary data
    """
    return get_prediction_arrays(athlete1, athlete2, event_name, base_transcript_dir)

def _clean_prediction_data(prediction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean and normalize prediction data for backend consistency.
    """
    # Convert empty strings, None, and "None" strings to None for consistency
    def clean_value(value):
        if value is None or value == "" or value == "None" or str(value).strip() == "":
            return None
        return str(value).strip() if value is not None else None
    
    # Safely get opinion_about_athletes, ensuring it's a dict
    opinion_data = prediction_data.get('opinion_about_athletes')
    if not isinstance(opinion_data, dict):
        opinion_data = {}
    
    cleaned = {
        "predictor": clean_value(prediction_data.get('predictor', '')),
        "match": prediction_data.get('match', []),
        "arm": clean_value(prediction_data.get('arm', '')),
        "event": clean_value(prediction_data.get('event', '')),
        "predicted_winner": clean_value(prediction_data.get('predicted_winner', '')),
        "predicted_score": clean_value(prediction_data.get('predicted_score', '')),
        "prediction_summary": clean_value(prediction_data.get('prediction_summary', '')),
        "predicted_duration": clean_value(prediction_data.get('predicted_duration', '')),
        "style_conflict": clean_value(prediction_data.get('style_conflict', '')),
        "confidence": clean_value(prediction_data.get('confidence', '')),
        "reasoning": clean_value(prediction_data.get('reasoning', '')),
        "opinion_about_athletes": opinion_data
    }
    
    # Clean opinion_about_athletes nested data
    for athlete, opinion in cleaned["opinion_about_athletes"].items():
        if isinstance(opinion, dict):
            cleaned["opinion_about_athletes"][athlete] = {
                "strength": clean_value(opinion.get('strength', '')),
                "health": clean_value(opinion.get('health', '')),
                "previous_match_summary": clean_value(opinion.get('previous_match_summary', ''))
            }
        else:
            # If opinion is not a dict, replace with empty dict
            cleaned["opinion_about_athletes"][athlete] = {
                "strength": None,
                "health": None,
                "previous_match_summary": None
            }
    
    return cleaned

def _remove_duplicate_predictions(predictions_array: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate predictions based on predictor and predicted_winner.
    Keep the one with more detailed information.
    """
    seen = {}
    unique_predictions = []
    
    for pred in predictions_array:
        key = f"{pred.get('predictor', '')}_{pred.get('predicted_winner', '')}"
        
        if key not in seen:
            seen[key] = pred
            unique_predictions.append(pred)
        else:
            # Keep the prediction with more detailed summary
            current_summary_length = len(pred.get('prediction_summary', '') or '')
            existing_summary_length = len(seen[key].get('prediction_summary', '') or '')
            
            if current_summary_length > existing_summary_length:
                # Replace with more detailed version
                for i, existing_pred in enumerate(unique_predictions):
                    if existing_pred == seen[key]:
                        unique_predictions[i] = pred
                        seen[key] = pred
                        break
    
    return unique_predictions

def get_prediction_arrays(athlete1: str, athlete2: str, event_name: str, base_transcript_dir: str = None) -> Dict[str, Any]:
    """
    Get prediction arrays with all detailed data for self and third party predictions.
    
    Returns:
        Dictionary containing 'self_predictions' and 'third_party_predictions' arrays with all data
    """
    predictions = extract_match_predictions(athlete1, athlete2, event_name, base_transcript_dir)
    
    if not predictions["match_found"]:
        return {
            "match": [athlete1, athlete2],
            "event": event_name,
            "self_predictions": [],
            "third_party_predictions": [],
            "match_found": False,
            "files_processed": predictions.get("files_processed", []),
            "summary": {
                "total_predictions": 0,
                "self_count": 0,
                "third_party_count": 0,
                "vote_distribution": {athlete1: 0, athlete2: 0},
                "consensus_favorite": None,
                "prediction_confidence": 0.0
            },
            "metadata": {
                "processed_at": None,
                "data_quality": "no_predictions_found"
            }
        }
    
    # Extract and clean detailed arrays
    self_predictions_array = []
    third_party_predictions_array = []
    
    for pred in predictions["self_predictions"]:
        cleaned_prediction = _clean_prediction_data({
            "predictor": pred.get('predictor', ''),
            "match": pred.get('match', []),
            "arm": pred.get('arm', ''),
            "event": pred.get('event', ''),
            "predicted_winner": pred.get('predicted_winner', ''),
            "predicted_score": pred.get('predicted_score', ''),
            "prediction_summary": pred.get('prediction_summary', ''),
            "predicted_duration": pred.get('predicted_duration', ''),
            "style_conflict": pred.get('style_conflict', ''),
            "confidence": pred.get('confidence', ''),
            "reasoning": pred.get('reasoning', ''),
            "opinion_about_athletes": pred.get('opinion_about_athletes', {})
        })
        self_predictions_array.append(cleaned_prediction)
    
    for pred in predictions["third_party_predictions"]:
        cleaned_prediction = _clean_prediction_data({
            "predictor": pred.get('predictor', ''),
            "match": pred.get('match', []),
            "arm": pred.get('arm', ''),
            "event": pred.get('event', ''),
            "predicted_winner": pred.get('predicted_winner', ''),
            "predicted_score": pred.get('predicted_score', ''),
            "prediction_summary": pred.get('prediction_summary', ''),
            "predicted_duration": pred.get('predicted_duration', ''),
            "style_conflict": pred.get('style_conflict', ''),
            "confidence": pred.get('confidence', ''),
            "reasoning": pred.get('reasoning', ''),
            "opinion_about_athletes": pred.get('opinion_about_athletes', {})
        })
        third_party_predictions_array.append(cleaned_prediction)
    
    # Remove duplicates
    self_predictions_array = _remove_duplicate_predictions(self_predictions_array)
    third_party_predictions_array = _remove_duplicate_predictions(third_party_predictions_array)
    
    # Calculate vote distribution and consensus
    athlete1_votes = 0
    athlete2_votes = 0
    total_predictions = len(self_predictions_array) + len(third_party_predictions_array)
    
    for pred in self_predictions_array + third_party_predictions_array:
        winner = pred.get("predicted_winner")
        # Skip if winner is None, empty, or invalid
        if not winner or winner == "None":
            continue
            
        if _fuzzy_match(winner, athlete1):
            athlete1_votes += 1
        elif _fuzzy_match(winner, athlete2):
            athlete2_votes += 1
    
    # Determine consensus
    consensus_favorite = None
    if athlete1_votes > athlete2_votes:
        consensus_favorite = athlete1
    elif athlete2_votes > athlete1_votes:
        consensus_favorite = athlete2
    
    # Calculate data quality metrics
    detailed_predictions = sum(1 for pred in self_predictions_array + third_party_predictions_array 
                              if pred.get('prediction_summary'))
    quality_score = detailed_predictions / total_predictions if total_predictions > 0 else 0
    
    return {
        "match": [athlete1, athlete2],
        "event": event_name,
        "self_predictions": self_predictions_array,
        "third_party_predictions": third_party_predictions_array,
        "match_found": True,
        "files_processed": predictions.get("files_processed", []),
        "summary": {
            "total_predictions": total_predictions,
            "self_count": len(self_predictions_array),
            "third_party_count": len(third_party_predictions_array),
            "vote_distribution": {
                athlete1: athlete1_votes, 
                athlete2: athlete2_votes
            },
            "consensus_favorite": consensus_favorite,
            "prediction_confidence": round(max(athlete1_votes, athlete2_votes) / total_predictions, 3) if total_predictions > 0 else 0.0
        },
        "metadata": {
            "processed_at": None,  # You can add timestamp here if needed
            "data_quality_score": round(quality_score, 3),
            "unique_predictors": len(set(pred.get('predictor') for pred in self_predictions_array + third_party_predictions_array if pred.get('predictor'))),
            "has_detailed_summaries": detailed_predictions > 0,
            "has_athlete_opinions": any(pred.get('opinion_about_athletes') for pred in self_predictions_array + third_party_predictions_array)
        }
    }
# Example usage and testing
if __name__ == "__main__":
    # Test with the example from your data
    athlete1 = "Bozhidar Simeonov"
    athlete2 = "Adam Wawrzynski"
    test_event = "East vs West 5"
    
    print(f"🔍 Searching for predictions: {athlete1} vs {athlete2} in {test_event}")
    
    # Extract predictions
    result = get_prediction_summary(athlete1, athlete2, test_event)
    
    # Print results
    if result["match_found"]:
        print(f"\n✅ Found {result['prediction_summary']['total_predictions']} total predictions")
        print(f"📊 Vote distribution: {result['prediction_summary']['vote_distribution']}")
        print(f"🏆 Consensus favorite: {result['prediction_summary']['consensus_favorite']}")
        
        # Save to file
        
        # Display some details
        # Create comprehensive arrays with all prediction data
        self_predictions_array = []
        third_party_predictions_array = []
        
        print(f"\n📝 Self predictions ({len(result['self_predictions'])}):")
        for pred in result["self_predictions"]:
            prediction_data = {
                "predictor": pred.get('predictor', ''),
                "match": pred.get('match', []),
                "arm": pred.get('arm', ''),
                "event": pred.get('event', ''),
                "predicted_winner": pred.get('predicted_winner', ''),
                "predicted_score": pred.get('predicted_score', ''),
                "prediction_summary": pred.get('prediction_summary', ''),
                "predicted_duration": pred.get('predicted_duration', ''),
                "style_conflict": pred.get('style_conflict', ''),
                "confidence": pred.get('confidence', ''),
                "reasoning": pred.get('reasoning', ''),
                "opinion_about_athletes": pred.get('opinion_about_athletes', {})
            }
            self_predictions_array.append(prediction_data)
            print(f"  - {pred['predictor']}: {pred['predicted_winner']} ({pred.get('predicted_score', 'N/A')})")
        
        print(f"\n🗣️ Third party predictions ({len(result['third_party_predictions'])}):")
        for pred in result["third_party_predictions"]:
            prediction_data = {
                "predictor": pred.get('predictor', ''),
                "match": pred.get('match', []),
                "arm": pred.get('arm', ''),
                "event": pred.get('event', ''),
                "predicted_winner": pred.get('predicted_winner', ''),
                "predicted_score": pred.get('predicted_score', ''),
                "prediction_summary": pred.get('prediction_summary', ''),
                "predicted_duration": pred.get('predicted_duration', ''),
                "style_conflict": pred.get('style_conflict', ''),
                "confidence": pred.get('confidence', ''),
                "reasoning": pred.get('reasoning', ''),
                "opinion_about_athletes": pred.get('opinion_about_athletes', {})
            }
            third_party_predictions_array.append(prediction_data)
            print(f"  - {pred['predictor']}: {pred['predicted_winner']} ({pred.get('predicted_score', 'N/A')})")
        
        print(f"\n📋 Arrays created:")
        print(f"   - self_predictions_array: {len(self_predictions_array)} items")
        print(f"   - third_party_predictions_array: {len(third_party_predictions_array)} items")
        
        # Optionally save arrays to separate files
       
    else:
        print("❌ No predictions found for this match")
        
    print(f"\n📁 Files processed: {result['files_processed']}")
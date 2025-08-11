# simple_test.py - Run this to debug your issue
import sys
from pathlib import Path

# Add your pipeline directory
sys.path.append(str(Path(__file__).resolve().parent))

# Import your function
from find_prediction import get_prediction_arrays, find_event_transcript_files

def test_step_by_step():
    athlete1 = "Devon Larratt"
    athlete2 = "Alex Kurdecha"
    event_name = "East vs West 18"
    
    print(f"🔍 Testing: {athlete1} vs {athlete2} in {event_name}")
    
    # Step 1: Check if files are found
    print("\n📁 Step 1: Finding transcript files...")
    files = find_event_transcript_files(event_name)
    print(f"Found {len(files)} files")
    
    if not files:
        print("❌ No files found - this is the problem!")
        print("Let's check what events are available...")
        
        # Check what events exist
        from pipeline.config import TRANSCRIPT_DIR
        transcript_dir = Path(TRANSCRIPT_DIR)
        
        if transcript_dir.exists():
            print("Available events:")
            for event_dir in transcript_dir.iterdir():
                if event_dir.is_dir():
                    identified_dir = event_dir / "Identified"
                    if identified_dir.exists():
                        file_count = len(list(identified_dir.glob("*.json")))
                        print(f"  📁 {event_dir.name} ({file_count} files)")
        return
    
    # Step 2: Test the full function
    print("\n🎯 Step 2: Running full prediction search...")
    result = get_prediction_arrays(athlete1, athlete2, event_name)
    
    print(f"Match found: {result['match_found']}")
    print(f"Files processed: {len(result.get('files_processed', []))}")
    print(f"Self predictions: {len(result.get('self_predictions', []))}")
    print(f"Third party predictions: {len(result.get('third_party_predictions', []))}")
    
    # Step 3: Show some details if found
    if result['match_found']:
        print("\n✅ Success! Sample predictions:")
        for pred in result.get('self_predictions', [])[:2]:
            print(f"  Self: {pred.get('predictor')} -> {pred.get('predicted_winner')}")
        for pred in result.get('third_party_predictions', [])[:2]:
            print(f"  Third: {pred.get('predictor')} -> {pred.get('predicted_winner')}")
    else:
        print("\n❌ No predictions found")

if __name__ == "__main__":
    test_step_by_step()
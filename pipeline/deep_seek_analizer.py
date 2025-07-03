import os
import json
import requests
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import SHALLOWSEEK_APIK



# Configuration
DEEPSEEK_API_KEY = SHALLOWSEEK_APIK  # Set your API key in environment variables
print(f"Using DeepSeek API Key: {DEEPSEEK_API_KEY}")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

def analyze_armwrestling_transcript(file_path):
    """Processes a transcript file and returns predictions in JSON format"""
    # Read the text file
    with open(file_path, 'r') as file:
        transcript = file.read()

    # Prepare the system prompt
    system_prompt = """
    You are an expert armwrestling analyst. Process interview transcripts and extract:
    1. Assign the participants usinf name of the file and context of the interview.
    2. JSON predictions for upcoming matches with:
        - predictor name
        - participants
        - predicted winner
        - event name
    3. compare the predictions with the actual results
    """

    # Create the API payload
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript}
        ],
        "temperature": 0.3,
        "max_tokens": 8000
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    # Call DeepSeek API
    response = requests.post(API_URL, headers=headers, json=payload)
    response_data = response.json()

    # Extract the content
    if 'choices' in response_data and response_data['choices']:
        content = response_data['choices'][0]['message']['content']
        return extract_response_components(content)
    
    raise Exception("API call failed: " + json.dumps(response_data, indent=2))

def extract_response_components(full_response):
    """Separates natural language response from JSON prediction"""
    # Try to find JSON block
    json_start = full_response.find('{')
    json_end = full_response.rfind('}') + 1
    
    if json_start != -1 and json_end != -1:
        json_str = full_response[json_start:json_end]
        summary = full_response[:json_start].strip()
        
        try:
            predictions = json.loads(json_str)
            return summary, predictions
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return full_response, None
    
    return full_response, None

def save_predictions(predictions, filename_prefix="predictions"):
    """Saves predictions to a JSON file with timestamp"""
    if not predictions:
        return None
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(predictions, f, indent=2)
    
    return filename

# Example Usage
if __name__ == "__main__":
    # Set your API key (better to use environment variables)
    # os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY

    
    # Process a transcript file
    try:
        summary, predictions = analyze_armwrestling_transcript("Cvetkov and Terzi.txt")
        
        print("\n==== SUMMARY ====")
        print(summary)
        
        if predictions:
            json_file = save_predictions(predictions)
            print(f"\n==== PREDICTIONS SAVED TO {json_file} ====")
            print(json.dumps(predictions, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
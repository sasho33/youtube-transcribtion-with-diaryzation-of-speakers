// src/api/matchPredictions.js
const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:5000";

export const fetchMatchPredictions = async (athlete1, athlete2, eventName) => {
  try {
    console.log("Fetching predictions for:", { athlete1, athlete2, eventName });
    
    // Use the main /match-predictions endpoint instead of /match-predictions-direct
    const response = await fetch(`${apiBase}/match-predictions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        athlete1: athlete1,
        athlete2: athlete2,
        event_name: eventName
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("API Error Response:", errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}\n${errorText}`);
    }

    const data = await response.json();
    console.log("API Response:", data);
    return data;
    
  } catch (error) {
    console.error("Error in fetchMatchPredictions:", error);
    throw error;
  }
};

// Alternative method using GET with query parameters
export const fetchMatchPredictionsWithQuery = async (athlete1, athlete2, eventName) => {
  try {
    console.log("Fetching predictions with query params for:", { athlete1, athlete2, eventName });
    
    const url = new URL(`${apiBase}/match-predictions/search`);
    url.searchParams.set('athlete1', athlete1);
    url.searchParams.set('athlete2', athlete2);
    url.searchParams.set('event_name', eventName);
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("API Error Response:", errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}\n${errorText}`);
    }

    const data = await response.json();
    console.log("API Response:", data);
    return data;
    
  } catch (error) {
    console.error("Error in fetchMatchPredictionsWithQuery:", error);
    throw error;
  }
};

// Get only summary data (lighter request)
export const fetchMatchPredictionsSummary = async (athlete1, athlete2, eventName) => {
  try {
    const url = new URL(`${apiBase}/match-predictions/summary`);
    url.searchParams.set('athlete1', athlete1);
    url.searchParams.set('athlete2', athlete2);
    url.searchParams.set('event_name', eventName);
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`Summary request failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Summary endpoint error:", error);
    throw error;
  }
};

// Test endpoint using the main match-predictions route
export const testMatchPredictionsEndpoint = async () => {
  try {
    // Test with a simple prediction request
    const testData = {
      athlete1: "Devon Larratt", 
      athlete2: "Alex Kurdecha", 
      event_name: "East vs West 18"
    };
    
    const response = await fetch(`${apiBase}/match-predictions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(testData)
    });

    if (!response.ok) {
      throw new Error(`Test endpoint failed: ${response.statusText}`);
    }

    const result = await response.json();
    return {
      status: "success",
      endpoint_working: true,
      match_found: result.match_found || false,
      predictions_found: result.summary?.total_predictions || 0,
      files_processed: result.files_processed?.length || 0
    };
  } catch (error) {
    console.error("Test endpoint error:", error);
    return {
      status: "error",
      endpoint_working: false,
      error: error.message
    };
  }
};
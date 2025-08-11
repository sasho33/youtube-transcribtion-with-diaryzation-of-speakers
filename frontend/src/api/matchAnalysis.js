// src/api/matchAnalysis.js
const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:5000";

/**
 * Fetch detailed match analysis including predictions, explanations, and historical data
 */
export const fetchMatchAnalysis = async (athlete1, athlete2, options = {}) => {
  try {
    console.log("Fetching enhanced match analysis for:", { athlete1, athlete2, options });
    
    const requestData = {
      athlete1_name: athlete1,
      athlete2_name: athlete2,
      match_arm: options.arm || 'Right',
      event_country: options.country || 'United States',
      event_title: options.eventTitle || '(Virtual)',
      event_date: options.date || undefined
    };

    const response = await fetch(`${apiBase}/match-analysis/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Enhanced Analysis API Error:", errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}\n${errorText}`);
    }

    const data = await response.json();
    console.log("Enhanced Analysis Response:", data);
    return data;
    
  } catch (error) {
    console.error("Error in fetchMatchAnalysis:", error);
    throw error;
  }
};

/**
 * Fetch quick match prediction without detailed analysis
 */
export const fetchQuickPrediction = async (athlete1, athlete2, options = {}) => {
  try {
    const url = new URL(`${apiBase}/match-analysis/quick`);
    url.searchParams.set('athlete1', athlete1);
    url.searchParams.set('athlete2', athlete2);
    url.searchParams.set('arm', options.arm || 'Right');
    url.searchParams.set('country', options.country || 'United States');
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Quick Prediction API Error:", errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("Quick Prediction Response:", data);
    return data;
    
  } catch (error) {
    console.error("Error in fetchQuickPrediction:", error);
    throw error;
  }
};

/**
 * Fetch detailed athlete comparison
 */
export const fetchAthleteComparison = async (athlete1, athlete2) => {
  try {
    const url = new URL(`${apiBase}/match-analysis/compare`);
    url.searchParams.set('athlete1', athlete1);
    url.searchParams.set('athlete2', athlete2);
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Athlete Comparison API Error:", errorText);
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("Athlete Comparison Response:", data);
    return data;
    
  } catch (error) {
    console.error("Error in fetchAthleteComparison:", error);
    throw error;
  }
};

/**
 * Test the enhanced match analysis endpoint
 */
export const testMatchAnalysisEndpoint = async () => {
  try {
    const response = await fetch(`${apiBase}/match-analysis/test`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`Test endpoint failed: ${response.statusText}`);
    }

    const result = await response.json();
    return {
      status: "success",
      endpoint_working: result.system_working || false,
      prediction_generated: result.prediction_generated || false,
      explanations_count: result.explanations_count || 0,
      shared_opponents_found: result.shared_opponents_found || 0,
      sample_probability: result.sample_probability || 0
    };
  } catch (error) {
    console.error("Enhanced analysis test endpoint error:", error);
    return {
      status: "error",
      endpoint_working: false,
      error: error.message
    };
  }
};

/**
 * Check API health and available endpoints
 */
export const checkApiHealth = async () => {
  try {
    const response = await fetch(`${apiBase}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Health check error:", error);
    throw error;
  }
};

/**
 * Helper function to format match analysis data for display
 */
export const formatAnalysisForDisplay = (analysisData) => {
  if (!analysisData) return null;

  const { prediction, analysis, athlete_profiles, valuable_matches } = analysisData;
  
  return {
    // Win probabilities formatted as percentages
    winProbabilities: {
      athlete1: {
        name: prediction.athlete1_name,
        probability: (prediction.athlete1_win_probability * 100).toFixed(1),
        confidence: prediction.confidence
      },
      athlete2: {
        name: prediction.athlete2_name,
        probability: (prediction.athlete2_win_probability * 100).toFixed(1),
        confidence: prediction.confidence
      }
    },
    
    // Key insights grouped by category
    insights: {
      physical: analysis.explanations.filter(exp => exp.category === 'Physical'),
      performance: analysis.explanations.filter(exp => exp.category === 'Performance'),
      experience: analysis.explanations.filter(exp => exp.category === 'Experience'),
      style: analysis.explanations.filter(exp => exp.category === 'Style'),
      history: analysis.explanations.filter(exp => exp.category === 'History')
    },
    
    // Simplified athlete data
    athletes: {
      athlete1: {
        ...athlete_profiles.athlete1,
        winRate: (athlete_profiles.athlete1.domestic_win_rate * 100).toFixed(1) + '%'
      },
      athlete2: {
        ...athlete_profiles.athlete2,
        winRate: (athlete_profiles.athlete2.domestic_win_rate * 100).toFixed(1) + '%'
      }
    },
    
    // Historical match summary
    history: {
      hasHeadToHead: valuable_matches.head_to_head.length > 0,
      headToHeadCount: valuable_matches.head_to_head.length,
      sharedOpponentsCount: valuable_matches.shared_opponents.length,
      commonConnections: valuable_matches.second_order_connections.length
    }
  };
};

/**
 * Helper function to get summary of key advantages/disadvantages
 */
export const getMatchSummary = (analysisData) => {
  if (!analysisData?.analysis?.explanations) return null;

  const explanations = analysisData.analysis.explanations;
  const advantages = explanations.filter(exp => exp.impact === 'positive');
  const disadvantages = explanations.filter(exp => exp.impact === 'negative');
  
  return {
    athlete1Name: analysisData.prediction.athlete1_name,
    athlete2Name: analysisData.prediction.athlete2_name,
    keyAdvantages: advantages.slice(0, 3), // Top 3 advantages
    keyDisadvantages: disadvantages.slice(0, 3), // Top 3 disadvantages
    overallFavorite: analysisData.prediction.athlete1_win_probability > 0.5 ? 
      analysisData.prediction.athlete1_name : 
      analysisData.prediction.athlete2_name,
    confidenceLevel: analysisData.prediction.confidence
  };
};
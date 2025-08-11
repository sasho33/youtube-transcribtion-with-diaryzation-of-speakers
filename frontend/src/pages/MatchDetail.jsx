// src/pages/MatchDetail.jsx
import { useEffect, useState } from "react";
import {
  Avatar, Box, Card, CardContent, Chip, CircularProgress, Divider,
  Grid, Stack, Typography, Button, Paper, Tab, Tabs, Alert
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PredictionsIcon from "@mui/icons-material/Psychology";
import InfoIcon from "@mui/icons-material/Info";
import { Link, useParams } from "react-router-dom";
import { athletes } from "../helpers/athletes_and_countries";
import { fetchMatchPredictions, testMatchPredictionsEndpoint } from "../api/matchPredictions";

const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

// Helper function to get athlete image
const getAthleteImage = (athleteName) => {
  const athlete = athletes.find(a => 
    a.name.toLowerCase().trim() === athleteName.toLowerCase().trim()
  );
  if (!athlete?.photo) return null;
  return athlete.photo.startsWith("http") 
    ? athlete.photo 
    : `${apiBase}/media/${athlete.photo}`;
};

// Helper function to format athlete name for URL
const formatAthleteUrl = (name) => encodeURIComponent(name.replace(/\s+/g, "_"));

// Prediction Card Component
function PredictionCard({ prediction, type }) {
  const isWinnerPrediction = prediction.predicted_winner;
  const winnerColor = isWinnerPrediction ? "success" : "default";

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Stack spacing={2}>
          {/* Predictor Header */}
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={1} alignItems="center">
              <Avatar sx={{ width: 32, height: 32, fontSize: "0.875rem" }}>
                {prediction.predictor?.charAt(0) || "?"}
              </Avatar>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                {prediction.predictor || "Unknown"}
              </Typography>
              <Chip 
                label={type === "self" ? "Self Prediction" : "Expert Opinion"} 
                size="small" 
                color={type === "self" ? "primary" : "secondary"}
                variant="outlined"
              />
            </Stack>
            {isWinnerPrediction && (
              <Chip 
                label={`Picks: ${prediction.predicted_winner}`} 
                size="small" 
                color={winnerColor}
                sx={{ fontWeight: 600 }}
              />
            )}
          </Stack>

          {/* Prediction Details */}
          <Grid container spacing={2}>
            {prediction.predicted_score && (
              <Grid item xs={6} sm={3}>
                <Typography variant="caption" color="text.secondary">Score</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {prediction.predicted_score}
                </Typography>
              </Grid>
            )}
            {prediction.arm && (
              <Grid item xs={6} sm={3}>
                <Typography variant="caption" color="text.secondary">Arm</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {prediction.arm}
                </Typography>
              </Grid>
            )}
            {prediction.predicted_duration && (
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary">Duration</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {prediction.predicted_duration}
                </Typography>
              </Grid>
            )}
            {prediction.confidence && (
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary">Confidence</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {prediction.confidence}
                </Typography>
              </Grid>
            )}
          </Grid>

          {/* Prediction Summary */}
          {prediction.prediction_summary && (
            <Box>
              <Typography variant="caption" color="text.secondary">Analysis</Typography>
              <Typography variant="body2" sx={{ mt: 0.5, fontStyle: "italic" }}>
                "{prediction.prediction_summary}"
              </Typography>
            </Box>
          )}

          {/* Additional Reasoning */}
          {prediction.reasoning && prediction.reasoning !== prediction.prediction_summary && (
            <Box>
              <Typography variant="caption" color="text.secondary">Additional Reasoning</Typography>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {prediction.reasoning}
              </Typography>
            </Box>
          )}

          {/* Style Conflict */}
          {prediction.style_conflict && (
            <Box>
              <Typography variant="caption" color="text.secondary">Style Matchup</Typography>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {prediction.style_conflict}
              </Typography>
            </Box>
          )}

          {/* Athlete Opinions */}
          {prediction.opinion_about_athletes && Object.keys(prediction.opinion_about_athletes).length > 0 && (
            <Box>
              <Typography variant="caption" color="text.secondary">Athlete Assessment</Typography>
              <Grid container spacing={1} sx={{ mt: 0.5 }}>
                {Object.entries(prediction.opinion_about_athletes).map(([athleteName, opinion]) => (
                  <Grid item xs={12} sm={6} key={athleteName}>
                    <Paper variant="outlined" sx={{ p: 1.5 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: "primary.main" }}>
                        {athleteName}
                      </Typography>
                      {opinion.strength && (
                        <Typography variant="body2" sx={{ fontSize: "0.75rem" }}>
                          <strong>Strength:</strong> {opinion.strength}
                        </Typography>
                      )}
                      {opinion.health && (
                        <Typography variant="body2" sx={{ fontSize: "0.75rem" }}>
                          <strong>Health:</strong> {opinion.health}
                        </Typography>
                      )}
                      {opinion.previous_match_summary && (
                        <Typography variant="body2" sx={{ fontSize: "0.75rem" }}>
                          <strong>Previous Matches:</strong> {opinion.previous_match_summary}
                        </Typography>
                      )}
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function MatchDetail() {
  const { source, eventTitle, matchId } = useParams();
  const [loading, setLoading] = useState(true);
  const [predictions, setPredictions] = useState(null);
  const [error, setError] = useState("");
  const [tabValue, setTabValue] = useState(0);

  // Parse match participants from matchId (format: "Athlete1-vs-Athlete2")
  const athletes_in_match = matchId ? matchId.split('-vs-').map(name => decodeURIComponent(name)) : [];
  const [athlete1, athlete2] = athletes_in_match;

  const athlete1Image = getAthleteImage(athlete1);
  const athlete2Image = getAthleteImage(athlete2);

  useEffect(() => {
    if (!athlete1 || !athlete2 || !eventTitle) {
      setError("Invalid match parameters");
      setLoading(false);
      return;
    }

    const fetchPredictions = async () => {
      try {
        setLoading(true);
        setError("");
        
        const decodedEventTitle = decodeURIComponent(eventTitle);
        console.log("Fetching predictions for:", {
          athlete1,
          athlete2,
          eventTitle: decodedEventTitle
        });

        // Test the endpoint first
        try {
          const testResult = await testMatchPredictionsEndpoint();
          console.log("Test endpoint result:", testResult);
          
          if (!testResult.endpoint_working) {
            throw new Error(`Endpoint test failed: ${testResult.error}`);
          }
        } catch (testError) {
          console.warn("Test endpoint failed:", testError);
          // Continue anyway - the main request might still work
        }

        // Fetch actual predictions using the main endpoint
        const data = await fetchMatchPredictions(
          athlete1, 
          athlete2, 
          decodedEventTitle
        );
        
        setPredictions(data);
        
        if (!data.match_found) {
          console.warn("No match found in predictions data");
        }
        
      } catch (err) {
        console.error("Error fetching predictions:", err);
        setError(err.message || "Failed to load predictions");
        setPredictions(null);
      } finally {
        setLoading(false);
      }
    };

    fetchPredictions();
  }, [athlete1, athlete2, eventTitle]);

  if (loading) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ mt: 6 }}>
        <CircularProgress size={60} />
        <Typography variant="h6">Loading match details...</Typography>
      </Stack>
    );
  }

  if (error || !athlete1 || !athlete2) {
    return (
      <Stack spacing={2}>
        <Button 
          component={Link} 
          to="/events" 
          startIcon={<ArrowBackIcon />} 
          size="large"
        >
          Back to Events
        </Button>
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h5" color="error" gutterBottom>
            Match Not Found
          </Typography>
          <Typography color="text.secondary">
            {error || "Invalid match parameters"}
          </Typography>
        </Paper>
      </Stack>
    );
  }

  const selfPredictions = predictions?.self_predictions || [];
  const thirdPartyPredictions = predictions?.third_party_predictions || [];
  const summary = predictions?.summary || {};
  const metadata = predictions?.metadata || {};

  return (
    <Stack spacing={3} sx={{ pb: 4 }}>
      {/* Navigation */}
      <Button 
        component={Link} 
        to={`/events/${source}/${eventTitle}`}
        startIcon={<ArrowBackIcon />} 
        size="large"
        sx={{ alignSelf: "flex-start" }}
      >
        Back to Event
      </Button>

      {/* Match Header */}
      <Paper alignSelf="center" sx={{ p: 4, textAlign: "center" }}>
        <Stack spacing={3}>
          <Typography variant="h4" sx={{ textAlign: "center", fontWeight: 700 }}>
            Match Analysis & Predictions
          </Typography>
          
          {/* Athletes Face-off */}
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} sm={5}>
              <Paper sx={{ p: 3, textAlign: "center" }}>
                <Avatar
                  src={athlete1Image}
                  alt={athlete1}
                  sx={{ width: 100, height: 100, mx: "auto", mb: 2 }}
                >
                  {athlete1?.charAt(0)}
                </Avatar>
                <Button
                  component={Link}
                  to={`/athletes/${formatAthleteUrl(athlete1)}`}
                  variant="text"
                  sx={{ textTransform: "none" }}
                >
                  <Typography variant="h5" sx={{ fontWeight: 600 }}>
                    {athlete1}
                  </Typography>
                </Button>
              </Paper>
            </Grid>

            <Grid item xs={12} sm={2}>
              <Box sx={{ textAlign: "center" }}>
                <Typography variant="h3" sx={{ fontWeight: 700, color: "primary.main" }}>
                  VS
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={5}>
              <Paper sx={{ p: 3, textAlign: "center" }}>
                <Avatar
                  src={athlete2Image}
                  alt={athlete2}
                  sx={{ width: 100, height: 100, mx: "auto", mb: 2 }}
                >
                  {athlete2?.charAt(0)}
                </Avatar>
                <Button
                  component={Link}
                  to={`/athletes/${formatAthleteUrl(athlete2)}`}
                  variant="text"
                  sx={{ textTransform: "none" }}
                >
                  <Typography variant="h5" sx={{ fontWeight: 600 }}>
                    {athlete2}
                  </Typography>
                </Button>
              </Paper>
            </Grid>
          </Grid>

          {/* Event Info */}
          <Stack direction="row" spacing={2} justifyContent="center" flexWrap="wrap">
            <Chip label={decodeURIComponent(eventTitle)} color="primary" />
            <Chip label={`${summary.total_predictions || 0} Total Predictions`} color="secondary" />
            {summary.consensus_favorite && (
              <Chip 
                label={`Consensus: ${summary.consensus_favorite}`} 
                color="success"
                sx={{ fontWeight: 600 }}
              />
            )}
            {metadata.processed_at && (
              <Chip 
                label={`Updated: ${new Date(metadata.processed_at).toLocaleDateString()}`} 
                size="small"
                variant="outlined"
              />
            )}
          </Stack>
        </Stack>
      </Paper>

      {/* Show files processed info if available */}
      {predictions?.files_processed && predictions.files_processed.length > 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="body2">
            Analyzed {predictions.files_processed.length} transcript file{predictions.files_processed.length !== 1 ? 's' : ''} 
            {metadata.data_quality_score && ` (Quality Score: ${Math.round(metadata.data_quality_score * 100)}%)`}
          </Typography>
        </Alert>
      )}

      {/* Predictions Summary */}
      {predictions?.match_found && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Prediction Summary</Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Typography variant="h4" color="primary.main" sx={{ fontWeight: 700 }}>
                {summary.total_predictions || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Predictions
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="h4" color="secondary.main" sx={{ fontWeight: 700 }}>
                {summary.self_count || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Self Predictions
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="h4" color="info.main" sx={{ fontWeight: 700 }}>
                {summary.third_party_count || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Expert Opinions
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="h4" color="success.main" sx={{ fontWeight: 700 }}>
                {Math.round((summary.prediction_confidence || 0) * 100)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Confidence
              </Typography>
            </Grid>
          </Grid>

          {/* Vote Distribution */}
          {summary.vote_distribution && Object.keys(summary.vote_distribution).length > 0 && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" gutterBottom>Vote Distribution</Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap">
                {Object.entries(summary.vote_distribution).map(([athlete, votes]) => (
                  <Chip 
                    key={athlete}
                    label={`${athlete}: ${votes} vote${votes !== 1 ? 's' : ''}`}
                    color={votes > 0 ? "primary" : "default"}
                    variant={votes > 0 ? "filled" : "outlined"}
                  />
                ))}
              </Stack>
            </Box>
          )}
        </Paper>
      )}

      {/* Predictions Tabs */}
      {predictions?.match_found ? (
        <Box>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab 
              icon={<InfoIcon />} 
              label={`Self Predictions (${selfPredictions.length})`} 
              iconPosition="start"
            />
            <Tab 
              icon={<PredictionsIcon />} 
              label={`Expert Opinions (${thirdPartyPredictions.length})`} 
              iconPosition="start"
            />
          </Tabs>

          <Box sx={{ mt: 3 }}>
            {tabValue === 0 && (
              <Stack spacing={2}>
                <Typography variant="h6">Self Predictions</Typography>
                {selfPredictions.length > 0 ? (
                  selfPredictions.map((prediction, index) => (
                    <PredictionCard 
                      key={`self-${index}`} 
                      prediction={prediction} 
                      type="self"
                    />
                  ))
                ) : (
                  <Paper sx={{ p: 3, textAlign: "center" }}>
                    <Typography variant="body1" color="text.secondary">
                      No self predictions found for this match.
                    </Typography>
                  </Paper>
                )}
              </Stack>
            )}

            {tabValue === 1 && (
              <Stack spacing={2}>
                <Typography variant="h6">Expert Opinions</Typography>
                {thirdPartyPredictions.length > 0 ? (
                  thirdPartyPredictions.map((prediction, index) => (
                    <PredictionCard 
                      key={`third-${index}`} 
                      prediction={prediction} 
                      type="third"
                    />
                  ))
                ) : (
                  <Paper sx={{ p: 3, textAlign: "center" }}>
                    <Typography variant="body1" color="text.secondary">
                      No expert predictions found for this match.
                    </Typography>
                  </Paper>
                )}
              </Stack>
            )}
          </Box>
        </Box>
      ) : (
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No Predictions Found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No prediction data is available for this match yet.
          </Typography>
          {predictions?.files_processed && predictions.files_processed.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              No transcript files were processed for this query.
            </Typography>
          )}
        </Paper>
      )}
    </Stack>
  );
}
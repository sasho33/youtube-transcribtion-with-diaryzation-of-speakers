
import { useEffect, useMemo, useState } from "react";
import {
  Avatar, Box, Card, CardContent, Chip, CircularProgress, Divider,
  Grid, Stack, Typography, Button, Paper
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SportsMmaIcon from "@mui/icons-material/SportsMma";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Link, useParams } from "react-router-dom";
import { fetchEventByTitle } from "../api/events";
import { eventLabel, colorFromText } from "../helpers/eventFormat";
import { athletes } from "../helpers/athletes_and_countries";

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

// Enhanced Match Component for Event Detail
function DetailedMatchCard({ match, eventTitle, source, index }) {
  const participants = match.participants || [];
  const isValidMatch = participants.length === 2;

  if (!isValidMatch) {
    return (
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
            {match.title || "Invalid match data"}
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const [athlete1, athlete2] = participants;
  const athlete1Image = getAthleteImage(athlete1);
  const athlete2Image = getAthleteImage(athlete2);

  return (
    <Card 
      variant="outlined" 
      sx={{ 
        mb: 2,
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          boxShadow: 4,
          transform: "translateY(-1px)"
        }
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Stack spacing={3}>
          {/* Match Header */}
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={2} alignItems="center">
              <Chip 
                label={`Match ${index + 1}`}
                size="medium"
                color="secondary"
                variant="outlined"
                sx={{ fontSize: { xs: "0.7rem", sm: "0.9rem", md: "1rem" } }}
              />
              <Chip 
                icon={<SportsMmaIcon />}
                label={match.arm + (match.arm.toLowerCase() == "left" ? "🫷" : " 🫸") || "Unknown Arm"} 
                size="medium"
                color="primary" 
                sx={{ fontSize: { xs: "0.7rem", sm: "0.9rem", md: "1rem" } }}
              />
              {match.score && (
                <Chip 
                  label={match.score} 
                  size="medium" 
                  color="info"
                  variant="outlined"
                  sx={{ fontSize: { xs: "0.7rem", sm: "0.9rem", md: "1rem" } }}
                />
              )}
            </Stack>
            {match.winner && (
              <Chip 
                label={`🏆 ${match.winner}`} 
                size="medium" 
                color="success"
                sx={{ 
                  fontSize: { xs: "0.7rem", sm: "0.9rem", md: "1rem" } ,
                  fontWeight: 600,
                  "& .MuiChip-label": {
                    px: 2
                  }
                }}
              />
            )}
          </Stack>

          {/* Athletes Face-off */}
          <Box>
            <Grid container spacing={3} alignItems="center">
              {/* Athlete 1 */}
              <Grid item size={{ xs: 12, sm: 5 }}>
                <Paper
                  variant="outlined"
                  sx={{ 
                    p: 2,
                    backgroundColor: match.winner === athlete1 ? "success.light" : "background.paper",
                    border: match.winner === athlete1 ? "2px solid" : "1px solid",
                    borderColor: match.winner === athlete1 ? "success.main" : "divider",
                    transition: "all 0.2s ease"
                  }}
                >
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Avatar
                      src={athlete1Image}
                      alt={athlete1}
                      sx={{ 
                        width: 60, 
                        height: 60,
                        border: "3px solid",
                        borderColor: match.winner === athlete1 ? "success.main" : "grey.300"
                      }}
                    >
                      {athlete1.charAt(0)}
                    </Avatar>
                    <Box sx={{ display: "flex", flexDirection: "column", alignItems:"center", minWidth: 0 }}>
                      <Button
                        component={Link}
                        to={`/athletes/${formatAthleteUrl(athlete1)}`}
                        variant="text"
                        sx={{ 
                          p: 0, 
                          textTransform: "none",
                          justifyContent: "flex-start",
                          "&:hover": {
                            backgroundColor: "transparent"
                          }
                        }}
                      >
                        <Typography 
                          variant="h6" 
                          sx={{ 
                            fontWeight: match.winner === athlete1 ? 700 : 500,
                            color: match.winner === athlete1 ? "success.dark" : "text.primary",
                            "&:hover": {
                              color: "primary.main"
                            }
                          }}
                          noWrap
                        >
                          {athlete1}
                        </Typography>
                      </Button>
                      {match.winner === athlete1 && (
                        <Typography  variant="caption" color="success.dark" sx={{ fontWeight: 600 }}>
                          WINNER
                        </Typography>
                      )}
                    </Box>
                  </Stack>
                </Paper>
              </Grid>

              {/* VS Separator */}
              <Grid item size={{ xs: 12, sm: 2 }}>
                <Box sx={{ textAlign: "center", py: 2 }}>
                  <Typography 
                    variant="h4" 
                    sx={{ 
                      fontWeight: 700,
                      color: "primary.main",
                      textShadow: "2px 2px 4px rgba(0,0,0,0.1)"
                    }}
                  >
                    VS
                  </Typography>
                </Box>
              </Grid>

              {/* Athlete 2 */}
              <Grid item size={{ xs: 12, sm: 5 }}>
                <Paper
                  variant="outlined"
                  sx={{ 
                    p: 2,
                    backgroundColor: match.winner === athlete2 ? "success.light" : "background.paper",
                    border: match.winner === athlete2 ? "2px solid" : "1px solid",
                    borderColor: match.winner === athlete2 ? "success.main" : "divider",
                    transition: "all 0.2s ease"
                  }}
                >
                  <Stack direction="row-reverse" spacing={2} alignItems="center">
                    <Avatar
                      src={athlete2Image}
                      alt={athlete2}
                      sx={{ 
                        width: 60, 
                        height: 60,
                        border: "3px solid",
                        borderColor: match.winner === athlete2 ? "success.main" : "grey.300"
                      }}
                    >
                      {athlete2.charAt(0)}
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0, textAlign: "right" }}>
                      <Button
                        component={Link}
                        to={`/athletes/${formatAthleteUrl(athlete2)}`}
                        variant="text"
                        sx={{ 
                          p: 0, 
                          textTransform: "none",
                          justifyContent: "flex-end",
                          "&:hover": {
                            backgroundColor: "transparent"
                          }
                        }}
                      >
                        <Typography 
                          variant="h6" 
                          sx={{ 
                            fontWeight: match.winner === athlete2 ? 700 : 500,
                            color: match.winner === athlete2 ? "success.dark" : "text.primary",
                            "&:hover": {
                              color: "primary.main"
                            }
                          }}
                          noWrap
                        >
                          {athlete2}
                        </Typography>
                      </Button>
                      {match.winner === athlete2 && (
                        <Typography variant="caption" color="success.dark" sx={{ fontWeight: 600 }}>
                          WINNER
                        </Typography>
                      )}
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
            </Grid>
          </Box>

          {/* Match Actions */}
          <Box sx={{ textAlign: "center", pt: 1 }}>
            <Button
              component={Link}
              to={`/matches/${source}/${encodeURIComponent(eventTitle)}/${encodeURIComponent(athlete1)}-vs-${encodeURIComponent(athlete2)}`}
              variant="contained"
              startIcon={<VisibilityIcon />}
              sx={{ 
                textTransform: "none",
                borderRadius: 2,
                px: 3
              }}
            >
              View Match Details & Predictions
            </Button>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function EventDetail() {
  const { source, eventTitle } = useParams();
  const title = useMemo(() => {
    if (!eventTitle) return "";
    try {
      return decodeURIComponent(eventTitle);
    } catch (e) {
      console.error("Failed to decode eventTitle:", eventTitle, e);
      return eventTitle;
    }
  }, [eventTitle]);

  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!source || !title) {
      setErr("Missing source or title parameters");
      setLoading(false);
      return;
    }

    let isMounted = true;
    
    (async () => {
      try {
        console.log("Fetching event:", { source, title });
        const data = await fetchEventByTitle(source, title);
        if (isMounted) {
          setEvent(data);
          setErr("");
        }
      } catch (e) {
        console.error("Failed to fetch event:", e);
        if (isMounted) setErr(e?.message || "Failed to load event");
      } finally {
        if (isMounted) setLoading(false);
      }
    })();
    
    return () => { isMounted = false; };
  }, [source, title]);

  if (loading) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ mt: 6 }}>
        <CircularProgress size={60} />
        <Typography variant="h6">Loading {title}…</Typography>
      </Stack>
    );
  }

  if (err || !event) {
    return (
      <Stack spacing={2}>
        <Button component={Link} to="/events" startIcon={<ArrowBackIcon />} size="large">
          Back to Events
        </Button>
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="h5" color="error" gutterBottom>
            Event Not Found
          </Typography>
          <Typography color="text.secondary" paragraph>
            {err || `We couldn't find "${title}".`}
          </Typography>
          <Typography variant="body2" color="text.disabled">
            Debug info: source={source}, eventTitle={eventTitle}, decodedTitle={title}
          </Typography>
        </Paper>
      </Stack>
    );
  }

  const badge = eventLabel(event.event_title);
  const badgeColor = colorFromText(badge);
  const matchCount = event.matches?.length || 0;

  return (
    <Stack spacing={3} sx={{ pb: 4 }} align="center">
      <Button 
        component={Link} 
        to="/events" 
        startIcon={<ArrowBackIcon />} 
        size="large"
        sx={{ alignSelf: "flex-start" }}
      >
        Back to Events
      </Button>

      {/* Event Header */}
      <Paper sx={{ p: 4 }} >
        <Stack direction="row" spacing={3} alignItems="center" justifyContent="center" alignSelf="center" align="center">
          <Avatar
            sx={{
              background: `linear-gradient(135deg, ${badgeColor} 0%, ${badgeColor}AA 100%)`,
              width: 100,
              height: 80,
              fontWeight: 700,
              fontSize: "1.5rem",
              borderRadius: "16px",
              boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
            }}
          >
            {badge}
          </Avatar>
          <Stack alignItems="center" sx={{ flex: 1 }}>
            <Typography variant="h3" sx={{ fontWeight: 700, mb: 1 }}>
              {event.event_title}
            </Typography>
            <Stack align="center" direction="row" spacing={2} flexWrap="wrap">
              <Chip label={event.event_date} color="primary" />
              <Chip label={event.event_location} variant="outlined" />
              <Chip label={`${matchCount} Match${matchCount !== 1 ? 'es' : ''}`} color="secondary" />
            </Stack>
          </Stack>
        </Stack>
      </Paper>

      <Divider />

      {/* Matches Section */}
      <Box>
        <Typography align="center" variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
          Matches
        </Typography>

        {matchCount > 0 ? (
          <Grid container spacing={2}>
            {event.matches.map((match, idx) => (
              <Grid item size={{ xs: 12 }} key={`match-${idx}`}>
                <DetailedMatchCard 
                  match={match} 
                  eventTitle={event.event_title}
                  source={source}
                  index={idx}
                />
              </Grid>
            ))}
          </Grid>
        ) : (
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No matches found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Match data might not be available for this event yet.
            </Typography>
          </Paper>
        )}
      </Box>
    </Stack>
  );
}
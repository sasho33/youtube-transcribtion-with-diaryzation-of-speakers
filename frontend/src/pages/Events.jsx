// src/pages/Events.jsx
import { useEffect, useState } from "react";
import { fetchEvents } from "../api/events";
import {
  Tabs, Tab, Grid, Card, CardContent, Typography, Stack, Avatar, 
  CardActionArea, Box, Chip, Button, Divider, Paper
} from "@mui/material";
import { Link } from "react-router-dom";
import { toSlug, eventLabel, colorFromText } from "../helpers/eventFormat";
import { sourceFromTitle } from "../helpers/events";
import { athletes } from "../helpers/athletes_and_countries";
import VisibilityIcon from "@mui/icons-material/Visibility";
import SportsMmaIcon from "@mui/icons-material/SportsMma";

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

// Enhanced Match Card Component
function MatchCard({ match, eventTitle, source }) {
  const participants = match.participants || [];
  const isValidMatch = participants.length === 2;

  if (!isValidMatch) {
    return (
      <Card variant="outlined" sx={{ mb: 1 }}>
        <CardContent sx={{ py: 1.5 }}>
          <Typography variant="body2" color="text.secondary">
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
          boxShadow: 3,
          transform: "translateY(-2px)"
        }
      }}
    >
      <CardContent>
        <Stack spacing={2}>
          {/* Match Header */}
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip 
                icon={<SportsMmaIcon />}
                label={match.arm || "Unknown Arm"} 
                size="small" 
                color="primary" 
                variant="outlined"
              />
              {match.score && (
                <Chip 
                  label={match.score} 
                  size="small" 
                  color="secondary"
                />
              )}
            </Stack>
            {match.winner && (
              <Chip 
                label={`Winner: ${match.winner}`} 
                size="small" 
                color="success"
                sx={{ fontWeight: 600 }}
              />
            )}
          </Stack>

          {/* Athletes Face-off */}
          <Box>
            <Grid container spacing={2} alignItems="center">
              {/* Athlete 1 */}
              <Grid item xs={5}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Avatar
                    src={athlete1Image}
                    alt={athlete1}
                    sx={{ 
                      width: 100, 
                      height: 50,
                      border: match.winner === athlete1 ? "3px solid #4caf50" : "2px solid #e0e0e0"
                    }}
                  >
                    {athlete1.charAt(0)}
                  </Avatar>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Button
                      component={Link}
                      to={`/athletes/${formatAthleteUrl(athlete1)}`}
                      variant="text"
                      size="small"
                      sx={{ 
                        p: 0, 
                        textTransform: "none",
                        justifyContent: "flex-start",
                        fontWeight: match.winner === athlete1 ? 700 : 500,
                        color: match.winner === athlete1 ? "success.main" : "text.primary",
                        "&:hover": {
                          backgroundColor: "transparent",
                          color: "primary.main"
                        }
                      }}
                    >
                      <Typography 
                        variant="body2" 
                        noWrap
                        sx={{ 
                          fontSize: "0.875rem",
                          fontWeight: "inherit",
                          color: "inherit"
                        }}
                      >
                        {athlete1}
                      </Typography>
                    </Button>
                  </Box>
                </Stack>
              </Grid>

              {/* VS Separator */}
              <Grid item xs={2}>
                <Box sx={{ textAlign: "center" }}>
                  <Typography 
                    variant="h6" 
                    sx={{ 
                      fontWeight: 700,
                      color: "text.secondary",
                      fontSize: "1rem"
                    }}
                  >
                    VS
                  </Typography>
                </Box>
              </Grid>

              {/* Athlete 2 */}
              <Grid item xs={5}>
                <Stack direction="row-reverse" spacing={2} alignItems="center">
                  <Avatar
                    src={athlete2Image}
                    alt={athlete2}
                    sx={{ 
                      width: 80, 
                      height: 50,
                      border: match.winner === athlete2 ? "3px solid #4caf50" : "2px solid #e0e0e0"
                    }}
                  >
                    {athlete2.charAt(0)}
                  </Avatar>
                  <Box sx={{ flex: 1, minWidth: 0, textAlign: "right" }}>
                    <Button
                      component={Link}
                      to={`/athletes/${formatAthleteUrl(athlete2)}`}
                      variant="text"
                      size="small"
                      sx={{ 
                        p: 0, 
                        textTransform: "none",
                        justifyContent: "flex-end",
                        fontWeight: match.winner === athlete2 ? 700 : 500,
                        color: match.winner === athlete2 ? "success.main" : "text.primary",
                        "&:hover": {
                          backgroundColor: "transparent",
                          color: "primary.main"
                        }
                      }}
                    >
                      <Typography 
                        variant="body2" 
                        noWrap
                        sx={{ 
                          fontSize: "0.875rem",
                          fontWeight: "inherit",
                          color: "inherit"
                        }}
                      >
                        {athlete2}
                      </Typography>
                    </Button>
                  </Box>
                </Stack>
              </Grid>
            </Grid>
          </Box>

          {/* Match Details Button */}
          <Box sx={{ textAlign: "center", pt: 1 }}>
            <Button
              component={Link}
              to={`/matches/${source}/${encodeURIComponent(eventTitle)}/${encodeURIComponent(athlete1)}-vs-${encodeURIComponent(athlete2)}`}
              variant="outlined"
              size="small"
              startIcon={<VisibilityIcon />}
              sx={{ 
                textTransform: "none",
                borderRadius: 2,
                "&:hover": {
                  backgroundColor: "primary.main",
                  color: "white"
                }
              }}
            >
              View Match Details
            </Button>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

// Enhanced Event Card Component
function EventCard({ event }) {
  const label = eventLabel(event.event_title);
  const bg = colorFromText(label);
  const source = sourceFromTitle(event.event_title);
  const matchCount = event.matches?.length || 0;

  return (
    <Box sx={{display: "flex", flexDirection: 'column', justifyContent: 'center', alignContent: 'center'}}>
    <Card 
      sx={{ 
        height: "100%",
        transition: "all 0.3s ease-in-out",
        "&:hover": {
          transform: "translateY(-4px)",
          boxShadow: 6,
          
        }
      }}
    >
      <CardActionArea 
        component={Link} 
        to={`/events/${source}/${encodeURIComponent(event.event_title)}`}
        
        sx={{ height: "100%" }}
      >
        <CardContent sx={{ height: "100%", display: "flex", flexDirection: "column", minWidth: "300px" }}>
          {/* Header */}
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <Avatar
              sx={{
                background: `linear-gradient(135deg, ${bg} 0%, ${bg}AA 100%)`,
                width: 80,
                height: 60,
                fontWeight: 700,
                fontSize: "1rem",
                borderRadius: "12px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
              }}
            >
              {label}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography 
                variant="h6" 
                sx={{ 
                  lineHeight: 1.2,
                  fontWeight: 600,
                  mb: 0.5
                }}
                noWrap
              >
                {event.event_title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {event.event_date}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {event.event_location}
              </Typography>
            </Box>
          </Stack>

          {/* Match Count & Preview */}
          <Box sx={{ mt: "auto" }}>
            <Divider sx={{ mb: 1 }} />
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Chip 
                label={`${matchCount} Match${matchCount !== 1 ? 'es' : ''}`} 
                size="small" 
                color="primary"
                variant="outlined"
              />
              <Typography variant="caption" color="primary.main" sx={{ fontWeight: 600 }}>
                View Details →
              </Typography>
            </Stack>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
    </Box>
  );
  
}

export default function Events() {
  const [tab, setTab] = useState("evw");
  const [data, setData] = useState({ count: 0, results: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    (async () => {
      try {
        const result = await fetchEvents(tab);
        setData(result);
      } catch (error) {
        console.error("Failed to fetch events:", error);
        setData({ count: 0, results: [] });
      } finally {
        setLoading(false);
      }
    })();
  }, [tab]);

  return (
    <Stack spacing={3} sx={{ pb: 4 }}>
      {/* Header */}
      <Box sx={{ textAlign: "center" }}>
        <Typography 
          variant="h3" 
          sx={{ 
            fontWeight: 700,
            background: "linear-gradient(45deg, #1976d2, #42a5f5)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            mb: 1
          }}
        >
          Events
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Discover armwrestling competitions and matches
        </Typography>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs 
          value={tab} 
          onChange={(_, v) => setTab(v)}
          centered
          sx={{
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 600,
              fontSize: "1rem"
            }
          }}
        >
          <Tab label="East vs West" value="evw" />
          <Tab label="King of the Table" value="kott" />
          <Tab label="All Events" value="" />
        </Tabs>
      </Box>

      {/* Loading State */}
      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography>Loading events...</Typography>
        </Box>
      )}

      {/* Events Grid */}
      {!loading && (
        <>
          <Typography variant="h6" color="text.secondary" sx={{ textAlign: "center" }}>
            {data.count} event{data.count !== 1 ? 's' : ''} found
          </Typography>
          
          <Grid container spacing={3}>
            {(data.results || []).map((event, index) => (
              <Grid key={`${event.event_title}-${event.event_date}-${index}`} item xs={12} sm={6} md={4} lg={3}>
                <EventCard event={event} />
              </Grid>
            ))}
            {data.results?.length === 0 && (
              <Grid item xs={12}>
                <Paper sx={{ p: 4, textAlign: "center" }}>
                  <Typography variant="h6" color="text.secondary">
                    No events found
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Try selecting a different category
                  </Typography>
                </Paper>
              </Grid>
            )}
          </Grid>
        </>
      )}
    </Stack>
  );
}
// src/pages/EventDetail.jsx
import { useEffect, useMemo, useState } from "react";
import {
  Avatar, Box, Card, CardContent, Chip, CircularProgress, Divider,
  Grid, Stack, Typography, Button
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Link, useParams } from "react-router-dom";
import { fetchEventByTitle } from "../api/events";
import { eventLabel, colorFromText } from "../helpers/eventFormat";

export default function EventDetail() {
  const { source, eventTitle } = useParams(); // Changed from 'slug' to 'eventTitle'
  const title = useMemo(() => {
    if (!eventTitle) return "";
    try {
      return decodeURIComponent(eventTitle);
    } catch (e) {
      console.error("Failed to decode eventTitle:", eventTitle, e);
      return eventTitle; // fallback to original eventTitle if decoding fails
    }
  }, [eventTitle]); // Changed dependency

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
        console.log("Fetching event:", { source, title }); // Debug log
        const data = await fetchEventByTitle(source, title);
        if (isMounted) {
          setEvent(data);
          setErr("");
        }
      } catch (e) {
        console.error("Failed to fetch event:", e); // Debug log
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
        <CircularProgress />
        <Typography>Loading {title}…</Typography>
      </Stack>
    );
  }

  if (err || !event) {
    return (
      <Stack spacing={2}>
        <Button component={Link} to="/events" startIcon={<ArrowBackIcon />}>
          Back to Events
        </Button>
        <Typography variant="h5">Not found</Typography>
        <Typography color="text.secondary">
          {err || `We couldn't find "${title}".`}
        </Typography>
        <Typography variant="body2" color="text.disabled" sx={{ mt: 2 }}>
          Debug info: source={source}, eventTitle={eventTitle}, decodedTitle={title}
        </Typography>
      </Stack>
    );
  }

  const badge = eventLabel(event.event_title);
  const badgeColor = colorFromText(badge);

  return (
    <Stack spacing={2}>
      <Button component={Link} to="/events" startIcon={<ArrowBackIcon />}>
        Back to Events
      </Button>

      <Stack direction="row" spacing={2} alignItems="center">
        
        <Avatar
  sx={{
    background: `linear-gradient(135deg, ${badgeColor} 0%, ${badgeColor}AA 100%)`, // gradient effect
    width: 70,
    height: 70,
    fontWeight: 700,
    fontSize: "1.2rem",
    borderRadius: "16px", // softer corners instead of a perfect circle
    boxShadow: "0 4px 10px rgba(0,0,0,0.2)", // subtle shadow for depth
  }}
>
  {badge}
</Avatar>
        <Stack>
          <Typography variant="h4">{event.event_title}</Typography>
          <Typography color="text.secondary">{event.event_date}</Typography>
          <Typography variant="body2" color="text.secondary">
            {event.event_location}
          </Typography>
        </Stack>
      </Stack>

      <Divider />

      <Typography variant="h6">Matches</Typography>

      <Grid container spacing={2}>
        {(event.matches || []).map((m, idx) => (
          <Grid item xs={12} key={idx}>
            <Card>
              <CardContent>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={2}
                  alignItems={{ xs: "flex-start", sm: "center" }}
                >
                  <Typography variant="subtitle1" sx={{ minWidth: 90 }}>
                    {m.arm || "—"}
                  </Typography>
                  <Typography variant="body1" sx={{ flex: 1 }}>
                    {m.participants?.length === 2
                      ? `${m.participants[0]} vs ${m.participants[1]}`
                      : (m.title || "Match")}
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    {m.winner && <Chip size="small" color="success" label={`Winner: ${m.winner}`} />}
                    {m.score && <Chip size="small" label={m.score} />}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {(!event.matches || event.matches.length === 0) && (
          <Grid item xs={12}>
            <Typography variant="body2">No matches found.</Typography>
          </Grid>
        )}
      </Grid>
    </Stack>
  );
}
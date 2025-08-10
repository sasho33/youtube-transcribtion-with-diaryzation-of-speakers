// src/pages/EventDetail.jsx
import { useEffect, useMemo, useState } from "react";
import {
  Avatar, Box, Card, CardContent, Chip, CircularProgress, Divider,
  Grid, Stack, Typography, Button
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Link, useParams } from "react-router-dom";
import { fetchEventByTitle } from "../api/events";
import { fromSlug, eventLabel, colorFromText } from "../helpers/eventFormat";

export default function EventDetail() {
  const { slug } = useParams();
  const title = useMemo(() => fromSlug(slug || ""), [slug]);
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchEventByTitle(title);
        setEvent(data);
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, [title]);

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
          {err || `We couldn’t find “${title}”.`}
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
        <Avatar sx={{ bgcolor: badgeColor, width: 56, height: 56, fontWeight: 700 }}>
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

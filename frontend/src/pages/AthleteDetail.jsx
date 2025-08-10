import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Paper,
} from "@mui/material";
import { Link, useParams } from "react-router-dom";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Button from "@mui/material/Button";
import { fetchAthlete } from "../api/athletes"; // must exist

const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";
const toImageSrc = (img) => {
  if (!img) return "";
  return img.startsWith("http") ? img : `${apiBase}/media/${img}`;
};

export default function AthleteDetail() {
  const { name } = useParams(); // e.g. "Vitaly_Laletin"

  const targetName = useMemo(
    () => decodeURIComponent(name || "").replace(/_/g, " ").trim(),
    [name]
  );

  const [athlete, setAthlete] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let ignore = false;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        // backend expects plain name with spaces, already decoded
        const data = await fetchAthlete(targetName);
        if (!ignore) setAthlete(data);
      } catch (e) {
        if (!ignore) setErr(e.message || "Failed to load athlete");
      } finally {
        if (!ignore) setLoading(false);
      }
    })();
    return () => { ignore = true; };
  }, [targetName]);

  if (loading) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ mt: 6 }}>
        <CircularProgress />
        <Typography>Loading {targetName}…</Typography>
      </Stack>
    );
  }

  if (err || !athlete) {
    return (
      <Stack spacing={2}>
        <Button component={Link} to="/athletes" startIcon={<ArrowBackIcon />}>
          Back to Athletes
        </Button>
        <Typography variant="h5">Not found</Typography>
        <Typography color="text.secondary">
          {err || `We couldn’t find “${targetName}”.`}
        </Typography>
      </Stack>
    );
  }

  const {
    name: fullName,
    country,
    gender,
    img, // note: JSON uses "img"
    age,
    height_cm,
    weight_kg,
    bicep_cm,
    forearm_cm,
    hand_size_cm,
    wingspan_cm,
    grip_strength_kg,
    dominant_arm,
    pulling_style = [],
    titles = [],
    win_loss_record,
    matches = {},
    nickname,
    training_location,
    occupation,
    date_of_birth,
  } = athlete;

  return (
    <Stack spacing={2}>
      <Button component={Link} to="/athletes" startIcon={<ArrowBackIcon />}>
        Back to Athletes
      </Button>

      <Typography variant="h4" align="center">{fullName}</Typography>
    <Grid container spacing={6} sx={{ mt: 2 }}>
        <Grid item size={{ xs: 12, sm: 6, md:4}}>  
          <Card>
        {/* Header image */}
        {img ? (
          
            <CardMedia
              component="img"
              src={toImageSrc(img)}
              alt={fullName}
              
              onError={(e) => { e.currentTarget.style.display = "none"; }}
            />
          
        ) : null}
      </Card>
        </Grid>
        <Grid item size={{ xs: 12,sm:6, md: 8 }}>
       
          <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
            {country && <Chip label={country} size="small" />}
            {gender && <Chip label={gender} size="small" sx={{ textTransform: "capitalize" }} />}
            {dominant_arm && <Chip label={`Dominant: ${dominant_arm}`} size="small" />}
            {nickname && <Chip label={`“${nickname}”`} size="small" />}
          </Stack>

          <Divider sx={{ my: 2 }} />

          {/* Quick facts */}
          <Grid container spacing={2} sx={{ minWidth: "100%" }}>
            <Grid item size={{ xs: 12, sm: 6}}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Profile</Typography>
                <Facts
                  data={{
                    "Date of birth": date_of_birth,
                    Age: age,
                    Country: country,
                    Gender: gender,
                    "Training location": training_location,
                    Occupation: occupation,
                  }}
                />
                {pulling_style?.length ? (
                  <>
                    <Typography variant="subtitle2" sx={{ mt: 1 }}>Pulling style</Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 0.5 }}>
                      {pulling_style.map((s) => <Chip key={s} label={s} size="small" />)}
                    </Stack>
                  </>
                ) : null}
              </Paper>
            </Grid>

            <Grid item size={{ xs: 12, sm: 6}}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Physical</Typography>
                <Facts
                  data={{
                    Height: height_cm ? `${height_cm} cm` : null,
                    Weight: weight_kg ? `${weight_kg} kg` : null,
                    Bicep: bicep_cm ? `${bicep_cm} cm` : null,
                    Forearm: forearm_cm ? `${forearm_cm} cm` : null,
                    "Hand size": hand_size_cm ? `${hand_size_cm} cm` : null,
                    Wingspan: wingspan_cm ? `${wingspan_cm} cm` : null,
                    "Grip strength": grip_strength_kg ? `${grip_strength_kg} kg` : null,
                  }}
                />
              </Paper>
            </Grid>
          </Grid>

          {/* Titles */}
          {titles?.length ? (
            <>
              <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Titles</Typography>
              <Stack spacing={0.5}>
                {titles.map((t, i) => (
                  <Typography key={i} variant="body2">• {t}</Typography>
                ))}
              </Stack>
            </>
          ) : null}

          {/* Record */}
          {win_loss_record ? (
            <>
              <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>Win/Loss Record</Typography>
              <Stack direction="row" spacing={2}>
                {win_loss_record.right && (
                  <Chip
                    label={`Right: ${win_loss_record.right.wins}-${win_loss_record.right.losses}`}
                    size="small"
                  />
                )}
                {win_loss_record.left && (
                  <Chip
                    label={`Left: ${win_loss_record.left.wins}-${win_loss_record.left.losses}`}
                    size="small"
                  />
                )}
              </Stack>
            </>
          ) : null}

        
        
      
        </Grid>
        
        <Grid item size={{xs:12}}>
          <Typography align="center" variant="h5" gutterBottom>Matches</Typography>
          {Object.keys(matches).length ? (
            <Stack spacing={1}>
              {Object.entries(matches).map(([opponent, matchList]) => (
                <Stack key={opponent} spacing={1} divider={<Divider flexItem />}>
                  {/* <Typography align="center" variant="subtitle1">{opponent}</Typography> */}
                  {matchList.map((m, i) => (
                    <MatchRow key={i} opponent={opponent} m={m} />
                  ))}
                </Stack>
              ))}
            </Stack>
          ) : (
            <Typography align="center" color="text.secondary">No matches found</Typography>
          )}
        </Grid>
      </Grid>
      
      {/* Matches */}
      
       
    </Stack>
  );
}

function Facts({ data }) {
  const rows = Object.entries(data).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (!rows.length) return <Typography variant="body2" color="text.secondary">No data</Typography>;
  return (
    <Stack spacing={0.5}>
      {rows.map(([k, v]) => (
        <Typography key={k} variant="body2">
          <b>{k}:</b> {v}
        </Typography>
      ))}
    </Stack>
  );
}

function MatchRow({ opponent, m }) {
  return (
    <Stack
      direction={ "row" }
      spacing={1}
      divider={<span />}
      sx={{ p: 1, borderRadius: 1, bgcolor: "background.default" }}
    >
      <Typography  variant="body1" sx={{ minWidth: 140 }}>{m.date || "—"}</Typography>
      <Typography  variant="body1" sx={{ flex: 1, }}>
        vs <b>{opponent}</b> • {m.arm || "—"} • {m.event || m.event_title || "—"}
      </Typography>
      <Typography variant="body1" align="left">
        {m.result ? (m.result.toLowerCase() === "win" ? "✅ Win" : m.result.toLowerCase() === "lost" ? "❌ Loss" : m.result) : "—"}
        {m.score ? ` (${m.score})` : ""}
      </Typography>
      {m.event_location && (
        <Typography variant="body1" color="text.secondary">{m.event_location}</Typography>
      )}
    </Stack>
  );
}

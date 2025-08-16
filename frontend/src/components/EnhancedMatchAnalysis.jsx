// src/components/PredictWithAthletePicker.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import dayjs from "dayjs";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardMedia,
  Chip,
  Divider,
  Grid,
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
  Alert,
  Tooltip,
  Snackbar,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  IconButton,
} from "@mui/material";
import {
  SwapHoriz as SwapHorizIcon,
  Person as PersonIcon,
  OpenInNew as OpenInNewIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Balance as BalanceIcon,
  ExpandMore as ExpandMoreIcon,
  Psychology as PsychologyIcon,
  OnlinePrediction,
  OnlinePredictionOutlined,
} from "@mui/icons-material";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";

import { athletes, countries } from "../helpers/athletes_and_countries";
import AiReviewPanel from "./AiReviewPanel";

const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:5000";

// --- helpers -----------------------------------------------------------------
const toImageSrc = (photo) => {
  if (!photo) return "";
  return photo.startsWith("http") ? photo : `${apiBase}/media/${photo}`;
};
const fmtPct = (x) => (x == null ? "—" : `${(x * 100).toFixed(1)}%`);
const fmtNum = (x) => (x == null ? "—" : (typeof x === "number" ? x : String(x)));
const safeAge = (age) => (age && age > 0 ? `${age}` : "—");
const impactColor = (impact) =>
  impact === "positive" ? "success" : impact === "negative" ? "error" : "info";
const ImpactIcon = ({ impact }) => {
  if (impact === "positive") return <TrendingUpIcon fontSize="small" />;
  if (impact === "negative") return <TrendingDownIcon fontSize="small" />;
  return <BalanceIcon fontSize="small" />;
};
const formatUrlName = (name) => encodeURIComponent(name.replace(/\s+/g, "_"));

// Group explanations by category
const groupByCategory = (exps = []) => {
  const order = [
    "Physical",
    "Experience",
    "Travel",
    "Performance",
    "Form",
    "History",
    "Comparison",
    "Other",
  ];
  const groups = exps.reduce((acc, e) => {
    const key = e.category || "Other";
    acc[key] = acc[key] || [];
    acc[key].push(e);
    return acc;
  }, {});
  // sort inside each group by absolute value desc
  for (const k of Object.keys(groups)) {
    groups[k].sort((a, b) => Math.abs(b.value ?? 0) - Math.abs(a.value ?? 0));
  }
  // return in preferred order
  return order
    .filter((k) => groups[k]?.length)
    .map((k) => ({ category: k, items: groups[k] }))
    .concat(
      Object.keys(groups)
        .filter((k) => !order.includes(k))
        .map((k) => ({ category: k, items: groups[k] }))
    );
};

// --- tiny blocks --------------------------------------------------------------
const Row = ({ label, value }) => (
  <Box display="flex" justifyContent="space-between">
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2" fontWeight={600}>{value ?? "—"}</Typography>
  </Box>
);

const WinProbabilityCard = ({ prediction }) => {
  const p1 = (prediction?.athlete1_win_probability ?? 0) * 100;
  const p2 = (prediction?.athlete2_win_probability ?? 0) * 100;
  return (
    <Card sx={{ mb: 3, background: "linear-gradient(135deg,#0f172a 0%,#1e293b 100%)", color: "white" }}>
      <CardContent sx={{ p: 4 }}>
        <Typography variant="h4" align="center" sx={{ fontWeight: 800, mb: 2 }}>
          Win Probability
        </Typography>
        <Grid container spacing={3} alignItems="center">
          <Grid item >
            <Box textAlign="center">
              <Typography variant="h3" sx={{ fontWeight: 800 }}>
                {p1.toFixed(1)}%
              </Typography>
              <Typography variant="h6">{prediction.athlete1_name}</Typography>
            </Box>
          </Grid>
          <Grid item>
            <Typography align="center" variant="h5" sx={{ opacity: 0.8 }}>VS</Typography>
          </Grid>
          <Grid item >
            <Box textAlign="center">
              <Typography variant="h3" sx={{ fontWeight: 800 }}>
                {p2.toFixed(1)}%
              </Typography>
              <Typography variant="h6">{prediction.athlete2_name}</Typography>
            </Box>
          </Grid>
        </Grid>
        <Box sx={{ mt: 3 }}>
          <LinearProgress
            variant="determinate"
            value={p1}
            sx={{
              height: 10,
              borderRadius: 6,
              backgroundColor: "rgba(255,255,255,0.25)",
              "& .MuiLinearProgress-bar": { borderRadius: 6 },
            }}
          />
        </Box>
        <Typography align="center" sx={{ mt: 1, opacity: 0.9 }}>
          Confidence: {prediction.confidence}
        </Typography>
      </CardContent>
    </Card>
  );
};

const ExplanationItem = ({ e }) => (
  <Paper variant="outlined" sx={{ p: 1.5 }}>
    <Stack direction="row" spacing={1.5} alignItems="center">
      <Chip size="small" icon={<ImpactIcon impact={e.impact} />} color={impactColor(e.impact)} label={e.category} variant="outlined" />
      <Box sx={{ flex: 1 }}>
        <Typography variant="subtitle2" fontWeight={700}>{e.title}</Typography>
        <Typography variant="body2" color="text.secondary">{e.description}</Typography>
      </Box>
      {e.value !== undefined && (
        <Typography variant="body2" fontWeight={700} color={`${impactColor(e.impact)}.main`}>
          {typeof e.value === "number" ? (e.value > 0 ? "+" : "") + Number(e.value).toFixed(1) : String(e.value)}
        </Typography>
      )}
    </Stack>
  </Paper>
);

const HeadToHead = ({ list }) => {
  if (!list || list.length === 0) return <Alert severity="info">No head-to-head history found.</Alert>;
  return (
    <Stack spacing={1.5}>
      {list.map((m, i) => (
        <Paper key={i} variant="outlined" sx={{ p: 1.5 }}>
          <Typography variant="subtitle2" fontWeight={700}>{m.event}</Typography>
          <Typography variant="body2" color="text.secondary">{m.date} • {m.arm} arm</Typography>
          <Typography variant="body2" sx={{ mt: .5 }}>
            {m.opponent}: {m.result} ({m.score})
          </Typography>
        </Paper>
      ))}
    </Stack>
  );
};

const SharedOpponents = ({ items }) => {
  if (!items || items.length === 0) return <Alert severity="info">No shared opponents available.</Alert>;
  return (
    <Stack spacing={1.5}>
      {items.map((s, idx) => (
        <Card key={idx} variant="outlined">
          <CardHeader align="center" title={`vs ${s.shared_opponent}`} sx={{ pb: 0 }} />
          <CardContent>
            <Grid container spacing={1.5}>
              {s.matches?.map((m, i) => (
                <Grid item size={{ xs: 12, md: 6 }}  key={i}>
                  <Paper variant="outlined"  sx={{ p: 1.5 }}>
                    <Typography align="center" variant="subtitle2" fontWeight={700}>
                      {m.participants?.[0]} vs {m.participants?.[1]}
                    </Typography>
                    <Typography align="center" variant="body2">Event: {m.event}</Typography>
                    <Typography align="center" variant="body2">Date: {m.date}</Typography>
                    <Typography align="center" variant="body2">Winner: <b>{m.winner}</b> ({m.score})</Typography>
                    <Chip align="center" size="small" label={m.arm} sx={{ mt: 1 }} />
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
};

const AthleteOption = ({ option }) => (
  <Stack direction="row" spacing={1.25} alignItems="center" sx={{ py: 0.5 }}>
    <Box sx={{ width: 40, height: 40, borderRadius: 1, overflow: "hidden", bgcolor: "action.hover" }}>
      {option.photo && (
        <img
          src={toImageSrc(option.photo)}
          alt={option.name}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          onError={(e) => { e.currentTarget.style.visibility = "hidden"; }}
        />
      )}
    </Box>
    <Box sx={{ minWidth: 0, textAlign: "center" }}>
      <Typography align="center" variant="body2" sx={{ fontWeight: 700, textAlign: "center" }} noWrap>{option.name} </Typography>
      <Typography align="center" variant="caption" color="text.secondary" noWrap>
        {option.country || "—"}
      </Typography>
    </Box>
  </Stack>
);

const SelectedAthleteCard = ({ label, athlete }) => (
  <Card variant="outlined" sx={{ height: "100%", minWidth: 300 }}>
    <CardHeader title={label} sx={{ pb: 0 }} />
    <CardContent>
      {athlete ? (
        <Stack spacing={1.25}>
          <Box sx={{ position: "relative", pt: "56.25%", borderRadius: 1, overflow: "hidden", bgcolor: "action.hover", height: 350 }}>
            {athlete.photo && (
              <CardMedia
                component="img"
                src={toImageSrc(athlete.photo)}
                alt={athlete.name}
                sx={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", }}
                onError={(e) => { e.currentTarget.style.display = "none"; }}
              />
            )}
          </Box>
          <Typography variant="h6" noWrap>{athlete.name}</Typography>
          <Typography variant="body2" color="text.secondary">{athlete.country || "—"}</Typography>
          <Stack align="center" direction="row" spacing={1}>
            {athlete.gender && <Chip size="small" label={athlete.gender} sx={{ textTransform: "capitalize" }} />}
            {athlete.dominant_arm && <Chip size="small" label={`Dom: ${athlete.dominant_arm}`} />}        
          </Stack>
          {/* Optional extra info if present in dataset */}
          <Grid container spacing={1}>
            {athlete.height_cm && (
              <Grid item xs={6}><Row label="Height" value={`${athlete.height_cm} cm`} /></Grid>
            )}
            {athlete.weight_kg && (
              <Grid item xs={6}><Row label="Weight" value={`${athlete.weight_kg} kg`} /></Grid>
            )}
            {athlete.dominant_style && (
              <Grid item xs={12}><Row label="Style" value={athlete.dominant_style} /></Grid>
            )}
          </Grid>
          <Button
            component={Link}
            to={`/athletes/${formatUrlName(athlete.name)}`}
            size="small"
            endIcon={<OpenInNewIcon />}
          >
            View profile
          </Button>
        </Stack>
      ) : (
        <Stack spacing={1} alignItems="center" sx={{ color: "text.secondary" }}>
          <PersonIcon />
          <Typography variant="body2">Choose an athlete</Typography>
        </Stack>
      )}
    </CardContent>
  </Card>
);

// --- main component -----------------------------------------------------------
export default function PredictWithAthletePicker() {

  const location = useLocation();
  const aiSectionRef = useRef(null);

  const [a1, setA1] = useState(null);
  const [a2, setA2] = useState(null);
  const [form, setForm] = useState({
    match_arm: "Right",
    event_country: "United States",
    event_title: "(Virtual)",
    event_date: "", // optional YYYY-MM-DD
  });
  const [dateValue, setDateValue] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [aiSnack, setAiSnack] = useState(false);

  const options1 = useMemo(() => athletes.filter((x) => !a2 || x.name !== a2.name), [a2]);
  const options2 = useMemo(() => athletes.filter((x) => !a1 || x.name !== a1.name), [a1]);
useEffect(() => {
  const params = new URLSearchParams(location.search);
  const name = params.get("athlete1");
  
  if (name) {
    const decoded = decodeURIComponent(name).trim().toLowerCase();
    console.log("decoded:", decoded);
    const found = athletes.find((a) =>
      a.name.trim().toLowerCase() === decoded
    );
   
    if (found) setA1(found);
  }
}, [location.search]);

  const handleFocus = () => {
  const el = aiSectionRef.current;
  if (!el) return;
  // scroll into view smoothly
  el.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
  // optionally give it programmatic focus for a11y (won't re-scroll because of preventScroll)
  el.focus?.({ preventScroll: true });
};
  const handleChange = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    if (!a1 || !a2) return;
    setLoading(true);
    setError("");
    setData(null);
    try {
      const payload = {
        athlete1: a1.name,
        athlete2: a2.name,
        match_arm: form.match_arm,
        event_country: form.event_country,
        event_title: form.event_title,
        ...(form.event_date ? { event_date: form.event_date } : {}),
      };
      const res = await fetch(`${apiBase}/predict/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${res.statusText} \n${t}`);
      }
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e.message || "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const swap = () => { setA1(a2); setA2(a1); };

  const topFactors = useMemo(() => {
    const exps = data?.analysis?.explanations || [];
    const positives = exps.filter((e) => e.impact === "positive");
    const negatives = exps.filter((e) => e.impact === "negative");
    const byMagnitude = (a, b) => Math.abs((b.value ?? 0)) - Math.abs((a.value ?? 0));
    return {
      positives: [...positives].sort(byMagnitude).slice(0, 3),
      negatives: [...negatives].sort(byMagnitude).slice(0, 3),
      grouped: groupByCategory(exps),
    };
  }, [data]);

  const rawFeaturesSorted = useMemo(() => {
    const entries = Object.entries(data?.raw_features || {});
    return entries.sort((a, b) => a[0].localeCompare(b[0]));
  }, [data]);

  return (
    <Stack spacing={3} sx={{
    justifyContent: "center",
    alignItems: "center",
  }}>
      {/* Picker */}
      <Card>
        <CardHeader
        align="center"
          title="Match Prediction"
          subheader="Pick athletes from your list, choose match details, then generate a prediction with full explanations"
          
        />
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item size={{ xs: 12, sm: 5 }}>
              <Autocomplete
                options={options1}
                value={a1}
                onChange={(_, v) => {
  setA1(v);
  if (!v || !a2) setData(null);
}}
                getOptionLabel={(o) => o?.name || ""}
                renderOption={(props, option) => (
                  <li {...props} key={option.name}>
                    <AthleteOption option={option} />
                  </li>
                )}
                renderInput={(params) => <TextField {...params} label="Athlete 1" />}
              />
            </Grid>
            <Grid item size={{ xs: 12, sm: 2 }} sx={{ display: "flex", justifyContent: "center" }}>
              <IconButton onClick={swap}><SwapHorizIcon /></IconButton>
            </Grid>
            <Grid item size={{ xs: 12, sm: 5 }}>
              <Autocomplete
                options={options2}
                value={a2}
                onChange={(_, v) => {
  setA2(v);
  if (!v || !a1) setData(null);
}}
                getOptionLabel={(o) => o?.name || ""}
                renderOption={(props, option) => (
                  <li {...props} key={option.name}>
                    <AthleteOption option={option} />
                  </li>
                )}
                renderInput={(params) => <TextField {...params} label="Athlete 2" />}
              />
            </Grid>

            {/* Event meta */}
            <Grid item size={{ xs: 6, sm: 6, md: 3 }}>
              <TextField select fullWidth label="Arm" value={form.match_arm} onChange={handleChange("match_arm")}>
                <MenuItem value="Right">Right</MenuItem>
                <MenuItem value="Left">Left</MenuItem>
              </TextField>
            </Grid>
            <Grid item size={{ xs: 6, sm: 6, md: 3 }}>
              <Autocomplete
                options={countries}
                value={form.event_country || null}
                onChange={(_, v) => setForm((f) => ({ ...f, event_country: v || "" }))}
                renderInput={(params) => <TextField {...params} label="Country" />}
              />
            </Grid>
            <Grid item size={{ xs: 6, sm: 6, md: 3 }}>
              <TextField fullWidth label="Event Title" value={form.event_title} onChange={handleChange("event_title")} />
            </Grid>
            <Grid item size={{ xs: 6, sm: 6, md: 3 }}>
              <LocalizationProvider dateAdapter={AdapterDayjs}>
                <DatePicker
                  label="Event Date"
                  value={dateValue}
                  onChange={(newVal) => {
                    setDateValue(newVal);
                    const iso = newVal ? dayjs(newVal).format("YYYY-MM-DD") : "";
                    setForm((f) => ({ ...f, event_date: iso }));
                  }}
                  slotProps={{ textField: { fullWidth: true } }}
                />
              </LocalizationProvider>
            </Grid>
          </Grid>

          <Stack direction="row" spacing={2} sx={{ display: "flex", alignItems: "center", justifyContent: "center", mt: 2 }}>
            <Button size="large" endIcon={<OnlinePredictionOutlined />} variant="contained" onClick={submit} disabled={loading || !a1 || !a2}>
              {loading ? "Predicting…" : "Predict"}
            </Button>
            <Button
  size="large"
  variant="outlined"
  startIcon={<PsychologyIcon />}
  onClick={handleFocus}
  disabled={!a1 || !a2}
>
  Enhance with AI
</Button>
          </Stack>
          {loading && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress />
            </Box>
          )}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
          )}
        </CardContent>
      </Card>

      {/* Selected previews with links */}
      <Grid container spacing={2}>
        <Grid item align="center" size={{ xs: 12, sm: 5 }}>
          <SelectedAthleteCard align="center" label="Athlete 1" athlete={a1} />
        </Grid>
        <Grid item size={{ xs: 12, sm: 2 }}>
          <Box display="flex" flexDirection="column" alignItems="end" justifyContent="center" sx={{ height: "100%" }}>
            <Typography variant="h3" fontWeight={"bold"} textAlign="center"> VS</Typography>
          </Box>
        </Grid>
        <Grid item align="center" size={{ xs: 12, sm: 5 }}>
          <SelectedAthleteCard align="center" label="Athlete 2" athlete={a2} />
        </Grid>
      </Grid>

      {/* Results */}
      {data && (
        <>
        <Box ref={aiSectionRef} tabIndex={1} sx={{ outline: "none" }}>
          <WinProbabilityCard prediction={data.prediction} />
</Box>
          {/* Predicted profile snapshot from API */}
          
          
            
           {a1 && a2 && (
  <AiReviewPanel
    athlete1Name={a1.name}
    athlete2Name={a2.name}
    matchArm={form?.match_arm || "Right"}
    eventCountry={form?.event_country || "United States"}
    eventTitle={form?.event_title || "(Virtual)"}
    eventDate={form?.event_date || ""}
  />
)}
          
          <Card>
            <CardHeader align="center" title="Predicted Profiles Snapshot" subheader="Key attributes from the prediction engine for each athlete" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography align="center" variant="h6" fontWeight={700} gutterBottom>
                      {data.athlete_profiles?.athlete1?.name || "Athlete 1"}
                    </Typography>
                    <Grid container spacing={2} ml={{xs:3, md:8, lg:20}} mr={{xs:3, md:8, lg:20}} columnSpacing={{ xs: 2, sm: 10, md: 30}} >
                      <Grid item size={{ xs: 6 }}><Row label="Country" value={data.athlete_profiles?.athlete1?.country} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Age" value={safeAge(data.athlete_profiles?.athlete1?.age)} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Weight" value={data.athlete_profiles?.athlete1?.weight_kg ? `${data.athlete_profiles.athlete1.weight_kg} kg` : "—"} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Height" value={data.athlete_profiles?.athlete1?.height_cm ? `${data.athlete_profiles.athlete1.height_cm} cm` : "—"} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Style" value={data.athlete_profiles?.athlete1?.dominant_style} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Secondary" value={data.athlete_profiles?.athlete1?.additional_style || "—"} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Streak" value={fmtNum(data.athlete_profiles?.athlete1?.current_winning_streak)} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Domestic WR" value={fmtPct(data.athlete_profiles?.athlete1?.domestic_win_rate)} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Transatlantic WR" value={fmtPct(data.athlete_profiles?.athlete1?.transatlantic_win_rate)} /></Grid>
                    </Grid>
                  </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography align="center" variant="h6" fontWeight={700} gutterBottom>
                      {data.athlete_profiles?.athlete2?.name || "Athlete 2"}
                    </Typography>
                    <Grid container  spacing={2} ml={{xs:3, md:8, lg:20}} mr={{xs:3, md:8, lg:20}} columnSpacing={{ xs: 2, sm: 10, md: 30}}>
                      <Grid item size={{ xs: 6 }}><Row label="Country" value={data.athlete_profiles?.athlete2?.country} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Age" value={safeAge(data.athlete_profiles?.athlete2?.age)} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Weight" value={data.athlete_profiles?.athlete2?.weight_kg ? `${data.athlete_profiles.athlete2.weight_kg} kg` : "—"} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Height" value={data.athlete_profiles?.athlete2?.height_cm ? `${data.athlete_profiles.athlete2.height_cm} cm` : "—"} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Style" value={data.athlete_profiles?.athlete2?.dominant_style} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Secondary" value={data.athlete_profiles?.athlete2?.additional_style || "—"} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Streak" value={fmtNum(data.athlete_profiles?.athlete2?.current_winning_streak)} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Domestic WR" value={fmtPct(data.athlete_profiles?.athlete2?.domestic_win_rate)} /></Grid>
                      <Grid item size={{ xs: 6 }}><Row label="Transatlantic WR" value={fmtPct(data.athlete_profiles?.athlete2?.transatlantic_win_rate)} /></Grid>
                    </Grid>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Why */}
          <Card>
            <CardHeader align="center" title="Why these probabilities?" subheader="Grouped impact factors with magnitudes" />
            <CardContent>
              <Grid container spacing={2}>
                {topFactors.grouped.map((group) => (
                  <Grid key={group.category} item size={{ xs: 12, md: 6 }}>
                    <Typography align="center" variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>{group.category}</Typography>
                    <Stack spacing={1.2}>
                      {group.items.map((e, i) => <ExplanationItem key={`${group.category}-${i}`} e={e} />)}
                    </Stack>
                  </Grid>
                ))}
              </Grid>
              {/* quick top 3/3 summary */}
              <Divider sx={{ my: 2 }} />
              <Grid container spacing={2}>
                <Grid item size={{ xs: 12, md: 6 }}>
                  <Typography align="center" variant="subtitle2" fontWeight={700}>Top Advantages</Typography>
                  <Stack spacing={1.2} sx={{ mt: 0.5 }}>
                    {topFactors.positives.length ? (
                      topFactors.positives.map((e, i) => <ExplanationItem key={`pos-${i}`} e={e} />)
                    ) : (
                      <Typography variant="body2" color="text.secondary">No major positive factors.</Typography>
                    )}
                  </Stack>
                </Grid>
                <Grid item size={{ xs: 12, md: 6 }}>
                  <Typography align="center" variant="subtitle2" fontWeight={700}>Top Disadvantages</Typography>
                  <Stack spacing={1.2} sx={{ mt: 0.5 }}>
                    {topFactors.negatives.length ? (
                      topFactors.negatives.map((e, i) => <ExplanationItem key={`neg-${i}`} e={e} />)
                    ) : (
                      <Typography variant="body2" color="text.secondary">No major negative factors.</Typography>
                    )}
                  </Stack>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Raw features & metadata (table) */}
          <Card>
            <CardHeader align="center" title="Model Features & Metadata" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item size={{ xs: 12, md: 8 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, overflow: "auto" }}>
                    <Typography variant="subtitle2" gutterBottom>Raw Features</Typography>
                    <Divider sx={{ mb: 1 }} />
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell>Feature</TableCell>
                          <TableCell align="right">Value</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {rawFeaturesSorted.map(([k, v]) => (
                          <TableRow key={k} hover>
                            <TableCell sx={{ fontFamily: "monospace" }}>{k}</TableCell>
                            <TableCell align="right">{String(v)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Paper>
                </Grid>
                <Grid item size={{ xs: 12, md: 4 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, height: "100%" }}>
                    <Typography variant="subtitle2" gutterBottom>Metadata</Typography>
                    <Divider sx={{ mb: 1 }} />
                    <Stack spacing={0.75}>
                      <Row label="Generated" value={new Date(data.metadata?.prediction_date).toLocaleString()} />
                      <Row label="Features" value={fmtNum(data.metadata?.model_features_count)} />
                      <Row label="Data Quality" value={data.metadata?.data_quality || "—"} />
                    </Stack>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* History */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader align="center" title="Head-to-Head" />
                <CardContent>
                  <HeadToHead list={data.valuable_matches?.head_to_head} />
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader align="center" title="Shared Opponents" />
                <CardContent>
                  <SharedOpponents items={data.valuable_matches?.shared_opponents} />
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Second-order connections (collapsible) */}
          <Accordion sx={{ mt: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography align="center" variant="subtitle1" fontWeight={700}>Second-order connections</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {Array.isArray(data.valuable_matches?.second_order_connections) && data.valuable_matches.second_order_connections.length ? (
                <Stack spacing={1.5}>
                  {data.valuable_matches.second_order_connections.map((row, idx) => {
                    const { a1_opponent, a2_opponent, shared_second_order, ...rest } = row;
                    const pairs = Object.entries(rest);
                    return (
                      <Paper key={idx} variant="outlined" sx={{ p: 1.5 }}>
                        <Grid container spacing={1}>
                          <Grid item size={{ xs: 12, md: 4 }}><Row label="A1 Opponent" value={a1_opponent} /></Grid>
                          <Grid item size={{ xs: 12, md: 4 }}><Row label="A2 Opponent" value={a2_opponent} /></Grid>
                          <Grid item size={{ xs: 12, md: 4 }}><Row label="Shared via" value={shared_second_order} /></Grid>
                        </Grid>
                        {pairs.length > 0 && (
                          <Table size="small" sx={{ mt: 1 }}>
                            <TableHead>
                              <TableRow>
                                <TableCell>Match</TableCell>
                                <TableCell>Outcome</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {pairs.map(([k, v]) => (
                                <TableRow key={k}>
                                  <TableCell sx={{ fontFamily: "monospace" }}>{k}</TableCell>
                                  <TableCell>{String(v)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        )}
                      </Paper>
                    );
                  })}
                </Stack>
              ) : (
                <Alert severity="info">No second-order connections found.</Alert>
              )}
            </AccordionDetails>
          </Accordion>

          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
            Powered by {apiBase}/predict/
          </Typography>
        </>
      )}

      {/* AI snackbar placeholder */}
      <Snackbar
        open={aiSnack}
        autoHideDuration={2000}
        onClose={() => setAiSnack(false)}
        message="AI enhancements coming soon"
      />
    </Stack>
  );
}

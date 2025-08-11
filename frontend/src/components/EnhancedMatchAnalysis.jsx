// src/components/PredictEnhanced.jsx
import React, { useMemo, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
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
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Balance as BalanceIcon,
} from "@mui/icons-material";

const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:5000";

// ---------- helpers ----------
const impactColor = (impact) =>
  impact === "positive" ? "success" : impact === "negative" ? "error" : "info";

const ImpactIcon = ({ impact }) => {
  if (impact === "positive") return <TrendingUpIcon fontSize="small" />;
  if (impact === "negative") return <TrendingDownIcon fontSize="small" />;
  return <BalanceIcon fontSize="small" />;
};

const fmtPct = (x) => (x == null ? "—" : `${(x * 100).toFixed(1)}%`);
const fmtNum = (x) => (x == null ? "—" : (typeof x === "number" ? x : String(x)));
const safeAge = (age) => (age && age > 0 ? `${age}` : "—");

// ---------- small UI blocks ----------
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
          <Grid item xs={12} md={5}>
            <Box textAlign="center">
              <Typography variant="h3" sx={{ fontWeight: 800 }}>
                {p1.toFixed(1)}%
              </Typography>
              <Typography variant="h6">{prediction.athlete1_name}</Typography>
            </Box>
          </Grid>
          <Grid item xs={12} md={2}>
            <Typography align="center" variant="h5" sx={{ opacity: 0.8 }}>VS</Typography>
          </Grid>
          <Grid item xs={12} md={5}>
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
              "& .MuiLinearProgress-bar": {
                borderRadius: 6,
              },
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

const AthleteCard = ({ title, a }) => (
  <Card variant="outlined" sx={{ height: "100%" }}>
    <CardHeader title={title} sx={{ pb: 0 }} />
    <CardContent>
      <Stack spacing={1.2}>
        <Row label="Name" value={a?.name} />
        <Row label="Country" value={a?.country} />
        <Row label="Age" value={safeAge(a?.age)} />
        <Row label="Weight" value={a?.weight_kg ? `${a.weight_kg} kg` : "—"} />
        <Row label="Height" value={a?.height_cm ? `${a.height_cm} cm` : "—"} />
        <Row label="Style" value={a?.dominant_style || "—"} />
        <Row label="Secondary" value={a?.additional_style || "—"} />
        <Row label="Win Streak" value={fmtNum(a?.current_winning_streak)} />
        <Row label="Domestic Win Rate" value={fmtPct(a?.domestic_win_rate)} />
        <Row label="Transatlantic Win Rate" value={fmtPct(a?.transatlantic_win_rate)} />
        {a?.is_title_holder && <Chip size="small" color="warning" label="Title Holder" />}
      </Stack>
    </CardContent>
  </Card>
);

const Row = ({ label, value }) => (
  <Box display="flex" justifyContent="space-between">
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2" fontWeight={600}>{value ?? "—"}</Typography>
  </Box>
);

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
          <CardHeader title={`vs ${s.shared_opponent}`} sx={{ pb: 0 }} />
          <CardContent>
            <Grid container spacing={1.5}>
              {s.matches?.map((m, i) => (
                <Grid item xs={12} md={6} key={i}>
                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" fontWeight={700}>
                      {m.participants?.[0]} vs {m.participants?.[1]}
                    </Typography>
                    <Typography variant="body2">Event: {m.event}</Typography>
                    <Typography variant="body2">Date: {m.date}</Typography>
                    <Typography variant="body2">Winner: <b>{m.winner}</b> ({m.score})</Typography>
                    <Chip size="small" label={m.arm} sx={{ mt: 1 }} />
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

// ---------- main component ----------
export default function PredictEnhanced() {
  const [form, setForm] = useState({
    athlete1: "",
    athlete2: "",
    match_arm: "Right",
    event_country: "United States",
    event_title: "(Virtual)",
    event_date: "", // YYYY-MM-DD optional
  });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setLoading(true);
    setError("");
    setData(null);
    try {
      const payload = { ...form };
      if (!payload.event_date) delete payload.event_date;
      // NOTE: backend expects keys: athlete1, athlete2, match_arm, event_country, event_title, event_date
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

  // derive quick explainer: top positive/negative factors
  const topFactors = useMemo(() => {
    const exps = data?.analysis?.explanations || [];
    const positives = exps.filter((e) => e.impact === "positive");
    const negatives = exps.filter((e) => e.impact === "negative");
    const byMagnitude = (a, b) => Math.abs((b.value ?? 0)) - Math.abs((a.value ?? 0));
    return {
      positives: [...positives].sort(byMagnitude).slice(0, 3),
      negatives: [...negatives].sort(byMagnitude).slice(0, 3),
    };
  }, [data]);

  return (
    <Stack spacing={3}>
      {/* Form */}
      <Card>
        <CardHeader title="Match Prediction" subheader="Powered by /predict/ endpoint (rich analysis)" />
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Athlete 1" value={form.athlete1} onChange={handleChange("athlete1")} />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Athlete 2" value={form.athlete2} onChange={handleChange("athlete2")} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField select fullWidth label="Arm" value={form.match_arm} onChange={handleChange("match_arm")}> 
                <MenuItem value="Right">Right</MenuItem>
                <MenuItem value="Left">Left</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField fullWidth label="Country" value={form.event_country} onChange={handleChange("event_country")} />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField fullWidth label="Event Title" value={form.event_title} onChange={handleChange("event_title")} />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField fullWidth label="Event Date (YYYY-MM-DD)" value={form.event_date} onChange={handleChange("event_date")} />
            </Grid>
          </Grid>
          <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
            <Button variant="contained" onClick={submit} disabled={loading || !form.athlete1 || !form.athlete2}>
              {loading ? "Predicting..." : "Predict"}
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

      {/* Results */}
      {data && (
        <>
          <WinProbabilityCard prediction={data.prediction} />

          {/* What influenced the result */}
          <Card>
            <CardHeader title="Why these probabilities?" subheader="Top contributing factors extracted from analysis.explanations" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>Key Advantages</Typography>
                  <Stack spacing={1.2}>
                    {topFactors.positives.length ? (
                      topFactors.positives.map((e, i) => <ExplanationItem key={`pos-${i}`} e={e} />)
                    ) : (
                      <Typography variant="body2" color="text.secondary">No major positive factors.</Typography>
                    )}
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>Key Disadvantages</Typography>
                  <Stack spacing={1.2}>
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

          {/* Athlete profiles */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <AthleteCard title="Athlete 1" a={data.athlete_profiles?.athlete1} />
            </Grid>
            <Grid item xs={12} md={6}>
              <AthleteCard title="Athlete 2" a={data.athlete_profiles?.athlete2} />
            </Grid>
          </Grid>

          {/* Detailed explanations */}
          <Card>
            <CardHeader title="All Factors & Explanations" />
            <CardContent>
              <Stack spacing={1.2}>
                {(data.analysis?.explanations || []).map((e, i) => (
                  <ExplanationItem key={i} e={e} />
                ))}
              </Stack>
            </CardContent>
          </Card>

          {/* Historical signals */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Head-to-Head" />
                <CardContent>
                  <HeadToHead list={data.valuable_matches?.head_to_head} />
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Shared Opponents" />
                <CardContent>
                  <SharedOpponents items={data.valuable_matches?.shared_opponents} />
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Raw features & metadata */}
          <Card>
            <CardHeader title="Model Features & Metadata" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={8}>
                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" gutterBottom>Raw Features</Typography>
                    <Divider sx={{ mb: 1 }} />
                    <Grid container spacing={1}>
                      {Object.entries(data.raw_features || {}).map(([k, v]) => (
                        <Grid key={k} item xs={12} sm={6}>
                          <Box display="flex" justifyContent="space-between">
                            <Typography variant="caption" color="text.secondary">{k}</Typography>
                            <Typography variant="caption" fontWeight={700}>{String(v)}</Typography>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  </Paper>
                </Grid>
                <Grid item xs={12} md={4}>
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

          <Typography variant="caption" color="text.secondary">
            Powered by {apiBase}/predict/
          </Typography>
        </>
      )}
    </Stack>
  );
}

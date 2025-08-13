// src/components/AiReviewPanel.jsx
import React, { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Grid,
  Link as MLink,
  LinearProgress,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Typography,
} from "@mui/material";
import {
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Balance as BalanceIcon,
} from "@mui/icons-material";

const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:5000";

const fmtPct = (x) => (x == null ? "—" : `${(x * 100).toFixed(1)}%`);
const impactChip = (dir) =>
  dir === "increase" ? { color: "success", icon: <TrendingUpIcon fontSize="small" /> } :
  dir === "decrease" ? { color: "error", icon: <TrendingDownIcon fontSize="small" /> } :
  { color: "info", icon: <BalanceIcon fontSize="small" /> };

const stageLabels = [
  "Ready",
  "Submitting request",
  "Waiting for DeepSeek",
  "Validating & formatting",
  "Done",
];

/**
 * AiReviewPanel
 * Props:
 *  - athlete1Name (string, required)
 *  - athlete2Name (string, required)
 *  - matchArm ("Right"|"Left", default "Right")
 *  - eventCountry (string, default "United States")
 *  - eventTitle (string, default "(Virtual)")
 *  - eventDate (YYYY-MM-DD | "")
 *  - onLoaded?: (aiReview) => void   // optional callback when data loaded
 */
export default function AiReviewPanel({
  athlete1Name,
  athlete2Name,
  matchArm = "Right",
  eventCountry = "United States",
  eventTitle = "(Virtual)",
  eventDate = "",
  onLoaded,
}) {
  const [aiData, setAiData] = useState(null);          // { ai_review: {...} }
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);               // 0..4

  const canEnhance = Boolean(athlete1Name && athlete2Name);

  const callEnhance = async () => {
    if (!canEnhance || loading) return;
    setError("");
    setAiData(null);
    setStage(1);
    setLoading(true);
    try {
      const payload = {
        athlete1_name: athlete1Name,
        athlete2_name: athlete2Name,
        match_arm: matchArm,
        event_country: eventCountry,
        event_title: eventTitle,
        ...(eventDate ? { event_date: eventDate } : {}),
      };

      const res = await fetch(`${apiBase}/ai-review/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      setStage(2);

      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status} ${res.statusText}\n${t}`);
      }

      const json = await res.json();
      setStage(3);

      if (!json || !json.ai_review) {
        throw new Error("Invalid response: missing ai_review");
      }

      setAiData(json);
      setStage(4);
      if (onLoaded) onLoaded(json.ai_review);
    } catch (e) {
      setError(e?.message || "AI enhancement failed");
      setStage(0);
    } finally {
      setLoading(false);
    }
  };

  const review = aiData?.ai_review || null;
  const adjusted = review?.adjusted_probabilities || null;
  const a1 = athlete1Name || (review?.meta?.athletes?.[0] ?? "Athlete 1");
  const a2 = athlete2Name || (review?.meta?.athletes?.[1] ?? "Athlete 2");

  const badges = useMemo(() => review?.ui_highlights?.badges || [], [review]);
  const cards  = useMemo(() => review?.ui_highlights?.highlight_cards || [], [review]);
  const timeline = useMemo(() => review?.ui_highlights?.timeline || [], [review]);
  const findings = useMemo(() => Array.isArray(review?.findings) ? review.findings : [], [review]);

  return (
    <Card variant="outlined">
      <CardHeader align="center"
        title="Enhance with AI"
        subheader="Runs live internet research (≤2 years), clarifies the model’s result, and returns structured evidence."
      />
      <CardContent>
        {/* Action row */}
        <Stack direction="row" spacing={2} alignItems="center" justifyContent="center" sx={{ mb: 2 }}>
          <Button
            variant="contained"
            size="large"
            startIcon={<PsychologyIcon />}
            onClick={callEnhance}
            disabled={!canEnhance || loading}
          >
            {loading ? "Enhancing…" : "Enhance with AI"}
          </Button>
          {!canEnhance && (
            <Alert severity="info" sx={{ m: 0 }}>
              Select both athletes first.
            </Alert>
          )}
        </Stack>

        {/* Stages */}
        <Box sx={{ mb: 2 }}>
          <Stepper activeStep={stage} alternativeLabel>
            {stageLabels.map((label, idx) => (
              <Step key={idx}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
          {loading && <LinearProgress sx={{ mt: 1 }} />}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Render ONLY when we have ai_review */}
        {review && (
          <Stack spacing={3}>
            {/* Adjusted Probabilities */}
            <Card>
              <CardHeader align="center"title="Adjusted Probabilities" subheader={review?.as_of ? `As of ${new Date(review.as_of).toLocaleString()}` : ""} />
              <CardContent>
                <Grid container spacing={2}>
                  <Grid item size={{ xs: 12, md: 6 }}>
                    <Paper variant="outlined" sx={{ p: 1.5 }}>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>{a1}</Typography>
                      <RowPair labelL="Before" valueL={fmtPct(adjusted?.before?.[a1])} labelR="After" valueR={fmtPct(adjusted?.after?.[a1])} />
                      <RowPair
                        labelL="Delta"
                        valueL={(adjusted?.deltas?.[a1] ?? 0) >= 0 ? `+${(adjusted?.deltas?.[a1] * 100).toFixed(1)}%` : `${(adjusted?.deltas?.[a1] * 100).toFixed(1)}%`}
                        labelR="Confidence"
                        valueR={adjusted?.confidence_tier || "—"}
                      />
                    </Paper>
                  </Grid>
                  <Grid item size={{ xs: 12, md: 6 }}>
                    <Paper variant="outlined" sx={{ p: 1.5 }}>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>{a2}</Typography>
                      <RowPair labelL="Before" valueL={fmtPct(adjusted?.before?.[a2])} labelR="After" valueR={fmtPct(adjusted?.after?.[a2])} />
                      <RowPair
                        labelL="Delta"
                        valueL={(adjusted?.deltas?.[a2] ?? 0) >= 0 ? `+${(adjusted?.deltas?.[a2] * 100).toFixed(1)}%` : `${(adjusted?.deltas?.[a2] * 100).toFixed(1)}%`}
                        labelR="Cap Applied"
                        valueR={String(Boolean(adjusted?.cap_applied))}
                      />
                    </Paper>
                  </Grid>
                </Grid>
                {adjusted?.reason && (
                  <Typography align="center" variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Reason: {adjusted.reason}
                  </Typography>
                )}
              </CardContent>
            </Card>

            {/* Summary & Narrative */}
            <Card>
              <CardHeader align="center" title="AI Summary" subheader="Bullet points + brief narrative" />
              <CardContent>
                <Grid container spacing={2}>
                  <Grid item size={{ xs: 12, md: 6 }}>
                    <Stack spacing={1}>
                      {(review.summary || []).map((s, i) => (
                        <Stack key={i} direction="row" spacing={1.5} alignItems="flex-start">
                          <Chip size="small" label={i + 1} />
                          <Typography variant="body2">{s}</Typography>
                        </Stack>
                      ))}
                      {(!review.summary || review.summary.length === 0) && (
                        <Typography variant="body2" color="text.secondary">No summary provided.</Typography>
                      )}
                    </Stack>
                  </Grid>
                  <Grid item size={{ xs: 12, md: 6 }}>
                    <Paper variant="outlined" sx={{ p: 1.5, height: "100%" }}>
                      <Typography variant="subtitle2" gutterBottom>Narrative</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {review.narrative || "—"}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            
            <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
                {/* Highlights */}
            <Card>
              <CardHeader align="center" title="Highlights" subheader="Badges • Cards • Timeline" />
              <CardContent align="center" justifyContent="center" alignItems="center">
                <Stack spacing={2} align="center">
                  {/* Badges */}
                  <Box align="center" sx={{ width: "100%" }}>
                    {badges.length ? (
                      <Stack direction="row" alignItems="center" justifyContent="center" spacing={1} flexWrap="wrap" useFlexGap>
                        {badges.map((b, i) => (
                          <Chip
                            align="center"
                            key={i}
                            color={b.type === "positive" ? "success" : b.type === "warning" ? "warning" : "info"}
                            label={`${b.label} — ${b.athlete_name}`}
                            title={b.tooltip || ""}
                            variant="outlined"
                            sx={{ mb: 1 }}
                          />
                        ))}
                      </Stack>
                    ) : (
                      <Typography align="center" variant="body2" color="text.secondary">No badges.</Typography>
                    )}
                  </Box>

                  {/* Cards */}
                  <Grid container spacing={2}>
                    {cards.length ? cards.map((c, i) => (
                      <Grid item size={{ xs: 12}} key={i}>
                        <Paper variant="outlined" sx={{ p: 1.5, height: "100%" }}>
                          <Typography variant="subtitle1" fontWeight={700}>{c.title}</Typography>
                          <Typography variant="caption" color="text.secondary">{c.subtitle}</Typography>
                          <Typography variant="body2" sx={{ mt: 1 }}>{c.snippet}</Typography>
                          {c.source_url && (
                            <Typography variant="body2" sx={{ mt: 1 }}>
                              <MLink href={c.source_url} target="_blank" rel="noopener">Source</MLink>
                              {c.published_at ? ` • ${c.published_at}` : ""}
                            </Typography>
                          )}
                        </Paper>
                      </Grid>
                    )) : (
                      <Grid item xs={12}>
                        <Typography variant="body2" color="text.secondary">No highlight cards.</Typography>
                      </Grid>
                    )}
                  </Grid>

                  {/* Timeline */}
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>Timeline</Typography>
                    {timeline.length ? (
                      <Stack spacing={1}>
                        {timeline.map((t, i) => (
                          <Stack key={i} direction="row" spacing={1.5} alignItems="center">
                            <Chip size="small" label={t.date || "—"} />
                            <Typography variant="body2" sx={{ flex: 1 }}>{t.label}</Typography>
                            {t.source_url && (
                              <MLink href={t.source_url} target="_blank" rel="noopener">Source</MLink>
                            )}
                          </Stack>
                        ))}
                      </Stack>
                    ) : (
                      <Typography variant="body2" color="text.secondary">No timeline entries.</Typography>
                    )}
                  </Box>
                </Stack>
              </CardContent>
            </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
                {/* Findings */}
            <Card align="center">
              <CardHeader title="Findings" subheader="Structured facts with impact and citations" />
              <CardContent>
                {findings.length ? (
                  <Stack spacing={1.5}>
                    {findings.map((f, i) => {
                      const { color, icon } = impactChip(f?.impact?.direction);
                      return (
                        <Paper key={i} variant="outlined" sx={{ p: 1.5 }}>
                          <Stack spacing={1}>
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Chip size="small" color={color} icon={icon} label={f.type || "note"} />
                              <Typography variant="subtitle2" fontWeight={700}>
                                {f.title || "Update"}
                              </Typography>
                            </Stack>
                            <Typography variant="body2" color="text.secondary">{f.detail || "—"}</Typography>
                            <Grid container spacing={1}>
                              <Grid item size={{ xs: 12, md: 4 }}>
                                <Row label="Athlete" value={f?.impact?.athlete_name} />
                              </Grid>
                              <Grid item size={{ xs: 6, md: 4 }}>
                                <Row label="Direction" value={f?.impact?.direction} />
                              </Grid>
                              <Grid item size={{ xs: 6, md: 4 }}>
                                <Row label="Magnitude" value={(f?.impact?.magnitude_pct != null) ? `${f.impact.magnitude_pct}%` : "—"} />
                              </Grid>
                            </Grid>
                            <Divider />
                            <Typography variant="caption" color="text.secondary">Evidence</Typography>
                            {Array.isArray(f.evidence) && f.evidence.length ? (
                              <Stack spacing={0.75}>
                                {f.evidence.map((e, j) => (
                                  <Typography key={j} variant="body2">
                                    <MLink href={e.url} target="_blank" rel="noopener">{e.source_title || e.url}</MLink>
                                    {e.publisher ? ` — ${e.publisher}` : ""} {e.published_at ? ` • ${e.published_at}` : ""}
                                  </Typography>
                                ))}
                              </Stack>
                            ) : (
                              <Typography variant="body2" color="text.secondary">No evidence listed.</Typography>
                            )}
                          </Stack>
                        </Paper>
                      );
                    })}
                  </Stack>
                ) : (
                  <Alert severity="info">No structured findings.</Alert>
                )}
              </CardContent>
            </Card>
            </Grid>

            </Grid>

            

            

            {/* Footer meta */}
            <Typography variant="caption" color="text.secondary">
              Prompt {review?.reproducibility?.prompt_version || "—"} • Model {review?.reproducibility?.model || "—"} • As-of {review?.as_of || "—"}
            </Typography>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

function RowPair({ labelL, valueL, labelR, valueR }) {
  return (
    <Stack direction="row" spacing={2} justifyContent="space-between">
      <Typography variant="body2"><b>{labelL}:</b> {valueL}</Typography>
      <Typography variant="body2"><b>{labelR}:</b> {valueR}</Typography>
    </Stack>
  );
}

function Row({ label, value }) {
  return <Typography variant="body2"><b>{label}:</b> {value ?? "—"}</Typography>;
}

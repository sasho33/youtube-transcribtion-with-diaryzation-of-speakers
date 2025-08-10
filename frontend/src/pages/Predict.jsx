import { useState } from "react";
import { postPrediction } from "../api/predict";
import { TextField, Button, Stack, Typography, Card, CardContent } from "@mui/material";

export default function Predict() {
  const [form, setForm] = useState({
    athlete1: "", athlete2: "",
    match_arm: "Right",
    event_country: "United States",
    event_title: "(Virtual)",
    event_date: "" // optional: YYYY-MM-DD
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    setResult(null);
    try {
      const payload = { ...form };
      if (!payload.event_date) delete payload.event_date;
      const r = await postPrediction(payload);
      setResult(r);
    } catch (e) {
      alert(e.message);
    } finally { setLoading(false); }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Prediction</Typography>
      <Stack direction="row" spacing={2}>
        <TextField label="Athlete 1" value={form.athlete1} onChange={e=>setForm(f=>({...f,athlete1:e.target.value}))}/>
        <TextField label="Athlete 2" value={form.athlete2} onChange={e=>setForm(f=>({...f,athlete2:e.target.value}))}/>
        <TextField label="Arm" value={form.match_arm} onChange={e=>setForm(f=>({...f,match_arm:e.target.value}))}/>
      </Stack>
      <Stack direction="row" spacing={2}>
        <TextField fullWidth label="Event Country" value={form.event_country} onChange={e=>setForm(f=>({...f,event_country:e.target.value}))}/>
        <TextField fullWidth label="Event Title" value={form.event_title} onChange={e=>setForm(f=>({...f,event_title:e.target.value}))}/>
        <TextField fullWidth label="Event Date (YYYY-MM-DD)" value={form.event_date} onChange={e=>setForm(f=>({...f,event_date:e.target.value}))}/>
      </Stack>
      <Button variant="contained" onClick={submit} disabled={loading}>Predict</Button>

      {result && (
        <Card>
          <CardContent>
            <Typography variant="h6">Result</Typography>
            <Typography>Probability (athlete1 wins): <b>{result.probability}</b></Typography>
            <Typography variant="body2">CSV saved at: {result.csv_saved_at}</Typography>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}

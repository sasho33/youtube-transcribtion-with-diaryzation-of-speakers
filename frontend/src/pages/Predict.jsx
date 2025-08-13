import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom"; 
import { postPrediction } from "../api/predict";
import { TextField, Button, Stack, Typography, Card, CardContent } from "@mui/material";

// helper to parse query params
function useQuery() {
  return new URLSearchParams(useLocation().search);
}

export default function Predict() {
  const location = useLocation();

  const [form, setForm] = useState({
  athlete1: "", athlete2: "",
  match_arm: "Right",
  event_country: "United States",
  event_title: "(Virtual)",
  event_date: ""
});

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

useEffect(() => {
  console.log("useEffect triggered");
  console.log("location:", location);
  console.log("location.search:", location.search);
  
  const params = new URLSearchParams(location.search);
  console.log("URLSearchParams:", params.toString());
  
  const athlete1FromQuery = params.get("athlete1");
  console.log("Athlete 1 from query:", athlete1FromQuery);
  
  if (athlete1FromQuery) {
    const decodedAthlete1 = decodeURIComponent(athlete1FromQuery);
    console.log("Decoded athlete1:", decodedAthlete1);
    setForm((f) => {
      console.log("Previous form state:", f);
      const newForm = { ...f, athlete1: decodedAthlete1 };
      console.log("New form state:", newForm);
      return newForm;
    });
  }
}, [location.search]);

// Also add this outside the useEffect to see the current form state
console.log("Current form state:", form);

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

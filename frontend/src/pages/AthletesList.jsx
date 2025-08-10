import { useEffect, useState } from "react";
import { fetchAthletes } from "../api/athletes";
import { TextField, Grid, Card, CardContent, Typography, Stack } from "@mui/material";
import { Link } from "react-router-dom";

export default function AthletesList() {
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("");
  const [data, setData] = useState({ count: 0, results: [] });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let ignore = false;
    (async () => {
      setLoading(true);
      try {
        const res = await fetchAthletes({ q, country });
        if (!ignore) setData(res);
      } finally { setLoading(false); }
    })();
    return () => { ignore = true; };
  }, [q, country]);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Athletes</Typography>
      <Stack direction="row" spacing={2}>
        <TextField label="Search name" value={q} onChange={e => setQ(e.target.value)} size="small"/>
        <TextField label="Country" value={country} onChange={e => setCountry(e.target.value)} size="small"/>
      </Stack>

      <Grid container spacing={2}>
        {data.results.map((a) => (
          <Grid key={a.name} item xs={12} sm={6} md={4}>
            <Card component={Link} to={`/athletes/${encodeURIComponent(a.name)}`} sx={{ textDecoration: "none" }}>
              <CardContent>
                <Typography variant="h6">{a.name}</Typography>
                <Typography variant="body2" color="text.secondary">{a.country || "—"}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {!loading && data.results.length === 0 && (
          <Typography variant="body2" sx={{ mt: 2 }}>No athletes found.</Typography>
        )}
      </Grid>
    </Stack>
  );
}

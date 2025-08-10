import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchAthlete } from "../api/athletes";
import { Typography, Stack, Card, CardContent } from "@mui/material";

export default function AthleteDetail() {
  const { name } = useParams();
  const [a, setA] = useState(null);

  useEffect(() => {
    (async () => setA(await fetchAthlete(decodeURIComponent(name))))();
  }, [name]);

  if (!a) return <Typography>Loading...</Typography>;

  return (
    <Stack spacing={2}>
      <Typography variant="h4">{a.name}</Typography>
      <Typography color="text.secondary">{a.country}</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">Profile</Typography>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{JSON.stringify(a, null, 2)}</pre>
        </CardContent>
      </Card>
    </Stack>
  );
}

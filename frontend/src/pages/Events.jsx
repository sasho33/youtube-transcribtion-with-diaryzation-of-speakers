import { useEffect, useState } from "react";
import { fetchEvents } from "../api/events";
import { Tabs, Tab, Grid, Card, CardContent, Typography, Stack } from "@mui/material";

export default function Events() {
  const [tab, setTab] = useState("evw");
  const [data, setData] = useState({ count: 0, results: [] });

  useEffect(() => {
    (async () => setData(await fetchEvents(tab)))();
  }, [tab]);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Events</Typography>
      <Tabs value={tab} onChange={(_,v) => setTab(v)}>
        <Tab label="East vs West" value="evw" />
        <Tab label="King of the Table" value="kott" />
      </Tabs>
      <Grid container spacing={2}>
        {data.results.map((e) => (
          <Grid key={`${e.event_title}-${e.event_date}`} item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6">{e.event_title}</Typography>
                <Typography color="text.secondary">{e.event_date}</Typography>
                <Typography variant="body2">{e.event_location}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}

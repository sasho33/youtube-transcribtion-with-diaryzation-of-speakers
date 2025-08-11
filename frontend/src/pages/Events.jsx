// src/pages/Events.jsx
import { useEffect, useState } from "react";
import { fetchEvents } from "../api/events";
import {
  Tabs, Tab, Grid, Card, CardContent, Typography, Stack, Avatar, CardActionArea
} from "@mui/material";
import { Link } from "react-router-dom";
import { toSlug, eventLabel, colorFromText } from "../helpers/eventFormat";
import { sourceFromTitle } from "../helpers/events";

export default function Events() {
  const [tab, setTab] = useState("evw");
  const [data, setData] = useState({ count: 0, results: [] });

  useEffect(() => {
    (async () => setData(await fetchEvents(tab)))();
  }, [tab]);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Events</Typography>

      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        <Tab label="East vs West" value="evw" />
        <Tab label="King of the Table" value="kott" />
        <Tab label="All" value="" />
      </Tabs>

      <Grid container spacing={2}>
        {(data.results || []).map((e) => {
          const label = eventLabel(e.event_title);
          const bg = colorFromText(label);
          return (
            <Grid key={`${e.event_title}-${e.event_date}`} item xs={12} sm={6} md={4} lg={3}>
              <Card>
                <CardActionArea  component={Link}  to={`/events/${sourceFromTitle(e.event_title)}/${encodeURIComponent(e.event_title)}`}>
                  <CardContent>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Avatar
  sx={{
    background: `linear-gradient(135deg, ${bg} 0%, ${bg}AA 100%)`, // gradient effect
    width: 70,
    height: 70,
    fontWeight: 700,
    fontSize: "1.2rem",
    borderRadius: "16px", // softer corners instead of a perfect circle
    boxShadow: "0 4px 10px rgba(0,0,0,0.2)", // subtle shadow for depth
  }}
>
  {label}
</Avatar>
                      <Stack>
                        <Typography variant="h6" sx={{ lineHeight: 1.1 }}>
                          {e.event_title}
                        </Typography>
                        <Typography color="text.secondary">{e.event_date}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {e.event_location}
                        </Typography>
                      </Stack>
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Stack>
  );
}

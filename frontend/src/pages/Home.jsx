import { Card, CardContent, Typography, Stack, Button } from "@mui/material";
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Welcome</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">Quick actions</Typography>
          <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
            <Button variant="contained" component={Link} to="/athletes">Browse Athletes</Button>
            <Button variant="outlined" component={Link} to="/events">Browse Events</Button>
            <Button variant="contained" color="secondary" component={Link} to="/predict">Try Prediction</Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

import { AppBar, Toolbar, Typography, Container, IconButton } from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { Link } from "react-router-dom";

export default function AppShell({ children }) {
  return (
    <>
      <AppBar position="sticky" elevation={0} >
        <Container maxWidth="lg">
        <Toolbar sx={{ gap: 2 }}>
          <IconButton edge="start" color="inherit"><MenuIcon /></IconButton>
          <Typography variant="h6" component={Link} to="/" style={{ color: "inherit", textDecoration: "none" }}>
            Armwrestling AI
          </Typography>
          <div style={{ flex: 1 }} />
          <Typography component={Link} to="/athletes" style={{ color: "inherit", textDecoration: "none", marginRight: 16 }}>
            Athletes
          </Typography>
          <Typography component={Link} to="/events" style={{ color: "inherit", textDecoration: "none", marginRight: 16 }}>
            Events
          </Typography>
          <Typography component={Link} to="/predict" style={{ color: "inherit", textDecoration: "none" }}>
            Predict
          </Typography>
        </Toolbar>
        </Container>
      </AppBar>
      <Container sx={{ py: 3 }}>{children}</Container>
    </>
  );
}

import { AppBar, Toolbar, Typography, Container, IconButton } from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { Link } from "react-router-dom";
import logo from "../assets/logo.png"; // Adjust the path as necessary

export default function AppShell({ children }) {
  return (
    <>
      <AppBar position="sticky" elevation={0} >
        <Container maxWidth="lg">
        <Toolbar sx={{ gap: 2 }}>
                    <img src={logo} alt="Logo" style={{ height: 40 }} />
          <Typography variant="h6" component={Link} to="/" style={{ color: "inherit", textDecoration: "none" }}>
            Armwrestling AI
          </Typography>
          <div style={{ flex: 1 }} />
          <Typography component={Link} to="/athletes" style={{ color: "inherit", textDecoration: "none", marginRight: 16, fontSize: { xs: '0.8rem', md: '1.2rem' } }}>
            Athletes
          </Typography>
          <Typography component={Link}  to="/events" style={{ color: "inherit", textDecoration: "none", marginRight: 16, fontSize: { xs: '0.8rem', md: '1.2rem' } }}>
            Events
          </Typography>
          <Typography component={Link} to="/predict" style={{ color: "inherit", textDecoration: "none", fontSize: { xs: '0.8rem', md: '1.2rem' } }}>
            Predict
          </Typography>
        </Toolbar>
        </Container>
      </AppBar>
      <Container sx={{ py: 3 }}>{children}</Container>
    </>
  );
}

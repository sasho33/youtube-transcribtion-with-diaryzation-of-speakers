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
            ArmFactor
          </Typography>
          <div style={{ flex: 1 }} />
          <Typography component={Link} to="/athletes" variant="h6" style={{ color: "inherit", textDecoration: "none", marginRight: 8, fontSize: { xs: 'h6', md: '1.5rem' } }}>
            Athletes
          </Typography>
          <Typography component={Link}  to="/events" variant="h6" style={{ color: "inherit", textDecoration: "none", marginRight: 8, fontSize: { xs: 'h6', md: '1.5rem' } }}>
            Events
          </Typography>
          <Typography component={Link} to="/predict" variant="h6" style={{ color: "inherit", textDecoration: "none", fontSize: { xs: 'h6', md: '1.5rem' } }}>
            Predict
          </Typography>
        </Toolbar>
        </Container>
      </AppBar>
      <Container sx={{ py: 3 }}>{children}</Container>
    </>
  );
}

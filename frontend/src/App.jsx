import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider, CssBaseline, Container } from "@mui/material";
import theme from "./theme";
import AppShell from "./components/AppShell";
import Home from "./pages/Home";
import AthletesList from "./pages/AthletesList";
import AthleteDetail from "./pages/AthleteDetail";
import Events from "./pages/Events";
import Predict from "./pages/Predict";

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppShell>
          <Container maxWidth="lg">
          <Routes>
            
            <Route path="/" element={<Home />} />
            <Route path="/athletes" element={<AthletesList />} />
            <Route path="/athletes/:name" element={<AthleteDetail />} />
            <Route path="/events" element={<Events />} />
            <Route path="/predict" element={<Predict />} />
          </Routes>
          </Container>
        </AppShell>
      </BrowserRouter>
    </ThemeProvider>
  );
}

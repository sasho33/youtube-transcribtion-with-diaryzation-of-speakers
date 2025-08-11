import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider, CssBaseline, Container } from "@mui/material";
import theme from "./theme";
import AppShell from "./components/AppShell";
import Home from "./pages/Home";
import AthletesList from "./pages/AthletesList";
import AthleteDetail from "./pages/AthleteDetail";
import Events from "./pages/Events";
import Predict from "./pages/Predict";
import ScrollToTop from "./components/ScrollToTop";
import EventDetail from "./pages/EventDetail";
import MatchDetail from "./pages/MatchDetail";

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {/* <Container maxWidth="lg"> */}
      <BrowserRouter>
        <AppShell>
          <ScrollToTop />
          <Routes>
            
            <Route path="/" element={<Home />} />
            <Route path="/athletes" element={<AthletesList />} />
            <Route path="/athletes/:name" element={<AthleteDetail />} />
            <Route path="/events" element={<Events />} />
            <Route path="/events/:source/:eventTitle" element={<EventDetail />} />
            <Route path="/predict" element={<Predict />} />
            <Route path="/matches/:source/:eventTitle/:matchId" element={<MatchDetail />} />
          </Routes>
          
        </AppShell>
      </BrowserRouter>
      {/* </Container> */}
    </ThemeProvider>
  );
}

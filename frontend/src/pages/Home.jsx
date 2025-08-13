import React, { useMemo, useState } from "react";
import {
  Box,
  Stack,
  Typography,
  Button,
  Card,
  CardContent,
  CardActionArea,
  CardMedia,
  Grid,
  Chip,
  Autocomplete,
  TextField,
  Divider,
} from "@mui/material";
import { Link, useNavigate } from "react-router-dom";
import {
  athletes,
} from "../helpers/athletes_and_countries";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import TimelineIcon from "@mui/icons-material/Timeline";
import SportsMmaIcon from "@mui/icons-material/SportsMma";
import BoltIcon from "@mui/icons-material/Bolt";
import SearchIcon from "@mui/icons-material/Search";

const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";
const toImageSrc = (photo) => (photo ? (photo.startsWith("http") ? photo : `${apiBase}/media/${photo}`) : "");

const formatUrlName = (name) => encodeURIComponent(name.replace(/\s+/g, "_"));

const AthleteOption = ({ option }) => (
  <Stack direction="row" spacing={1.25} alignItems="center" sx={{ py: 0.5 }}>
    <Box
      sx={{
        width: 40,
        height: 40,
        borderRadius: 1,
        overflow: "hidden",
        bgcolor: "action.hover",
        flexShrink: 0,
      }}
    >
      {option.photo && (
        <img
          src={toImageSrc(option.photo)}
          alt={option.name}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
          onError={(e) => (e.currentTarget.style.visibility = "hidden")}
        />
      )}
    </Box>
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="body2" noWrap>{option.name}</Typography>
      <Typography variant="caption" color="text.secondary" noWrap>
        {option.country || "—"}
      </Typography>
    </Box>
  </Stack>
);

export default function Home() {
  const navigate = useNavigate();
  const [nameQuery, setNameQuery] = useState("");

  const featuredAthletes = useMemo(() => {
    // Prioritize those with photos, then alphabetically
    const copy = [...athletes];
    copy.sort((a, b) => {
      const ap = a.photo ? 0 : 1;
      const bp = b.photo ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return a.name.localeCompare(b.name);
    });
    return copy.slice(0, 8);
  }, []);

  const totalAthletes = athletes?.length || 0;

  return (
    <Stack spacing={3} sx={{ pb: 4 }}>
      {/* HERO */}
      <Box
        sx={{
          position: "relative",
          p: { xs: 3, md: 5 },
          borderRadius: 3,
          overflow: "hidden",
          color: "common.white",
          background:
            "radial-gradient(1000px circle at -10% -10%, rgba(255,255,255,0.12), transparent 40%), linear-gradient(135deg, #0f172a, #1e293b)",
          boxShadow: (t) => t.shadows[6],
        }}
      >
        <Stack spacing={2.5}>
          <Stack spacing={1}>
            <Chip
              icon={<BoltIcon />}
              label="New: Enhanced Match Analysis"
              variant="outlined"
              sx={{
                alignSelf: "flex-start",
                color: "common.white",
                borderColor: "rgba(255,255,255,0.3)",
                bgcolor: "rgba(255,255,255,0.06)",
              }}
              component={Link}
              to="/predict"
              clickable
            />
            <Typography variant="h3" fontWeight={800} lineHeight={1.2}>
              Welcome — dive into match intelligence
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.9, maxWidth: 720 }}>
              Explore athletes, study head-to-heads, and build your own predictions.
            </Typography>
          </Stack>

          {/* Quick CTAs */}
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button
              variant="contained"
              color="secondary"
              startIcon={<BoltIcon />}
              component={Link}
              to="/predict"
            >
              Try Predictor
            </Button>
            <Button
              variant="outlined"
              startIcon={<TimelineIcon />}
              component={Link}
              to="/predict"
              sx={{ color: "common.white", borderColor: "rgba(255,255,255,0.4)" }}
            >
              Enhanced Analysis
            </Button>
            <Button
              variant="outlined"
              startIcon={<EmojiEventsIcon />}
              component={Link}
              to="/events"
              sx={{ color: "common.white", borderColor: "rgba(255,255,255,0.4)" }}
            >
              Browse Events
            </Button>
          </Stack>

          {/* Athlete quick search */}
          <Box
            sx={{
              mt: 1,
              maxWidth: 560,
              bgcolor: "background.paper",
              borderRadius: 2,
              p: 1,
              boxShadow: (t) => t.shadows[8],
            }}
          >
            <Autocomplete
              fullWidth
              freeSolo
              options={athletes}
              getOptionLabel={(o) => (typeof o === "string" ? o : o?.name || "")}
              isOptionEqualToValue={(o, v) => o?.name === v?.name}
              inputValue={nameQuery}
              onInputChange={(_, val) => setNameQuery(val || "")}
              onChange={(_, val) => {
                const name = typeof val === "string" ? val : val?.name;
                if (name) navigate(`/athletes/${formatUrlName(name)}`);
              }}
              renderOption={(props, option) => (
                <li {...props} key={option.name}>
                  <AthleteOption option={option} />
                </li>
              )}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Search athlete"
                  size="medium"
                  InputProps={{
                    ...params.InputProps,
                    startAdornment: <SearchIcon sx={{ mr: 1, opacity: 0.7 }} />,
                  }}
                />
              )}
            />
          </Box>

          {/* Small stats row */}
          <Stack direction="row" spacing={1.5} sx={{ mt: 0.5 }} flexWrap="wrap">
            <Chip
              icon={<SportsMmaIcon />}
              label={`${totalAthletes} athletes`}
              sx={{ bgcolor: "rgba(255,255,255,0.08)", color: "common.white" }}
            />
            <Chip
              icon={<TimelineIcon />}
              label="Head-to-head insights"
              sx={{ bgcolor: "rgba(255,255,255,0.08)", color: "common.white" }}
            />
            <Chip
              icon={<EmojiEventsIcon />}
              label="Event breakdowns"
              sx={{ bgcolor: "rgba(255,255,255,0.08)", color: "common.white" }}
            />
          </Stack>
        </Stack>
      </Box>

      {/* Feature cards */}
      <Grid container spacing={2}>
        <Grid item size={{ xs: 12, md: 4 }}>
          <Card sx={{ height: "100%", borderRadius: 3, ":hover": { transform: "translateY(-2px)" }, transition: "0.2s" }}>
            <CardActionArea component={Link} to="/predict" sx={{ height: "100%" }}>
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center">
                  <TimelineIcon />
                  <Typography variant="h6">Enhanced Match Analysis</Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Compare styles, recent form, and outcomes in one place.
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
        <Grid item size={{ xs: 12, md: 4 }}>
          <Card sx={{ height: "100%", borderRadius: 3, ":hover": { transform: "translateY(-2px)" }, transition: "0.2s" }}>
            <CardActionArea component={Link} to="/predict" sx={{ height: "100%" }}>
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center">
                  <BoltIcon />
                  <Typography variant="h6">Predictor</Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Generate win probabilities using your chosen inputs.
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
        <Grid item size={{ xs: 12, md: 4 }}>
          <Card sx={{ height: "100%", borderRadius: 3, ":hover": { transform: "translateY(-2px)" }, transition: "0.2s" }}>
            <CardActionArea component={Link} to="/events" sx={{ height: "100%" }}>
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center">
                  <EmojiEventsIcon />
                  <Typography variant="h6">Events</Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Browse cards, results, and past matchups by event.
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
      </Grid>

      {/* Featured athletes */}
      <Box>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="h5" fontWeight={700}>Featured Athletes</Typography>
          <Button component={Link} to="/athletes" size="small">See all</Button>
        </Stack>
        <Divider sx={{ mb: 2 }} />
        <Grid container spacing={2}>
          {featuredAthletes.map((a) => (
            <Grid key={a.name} item size={{ xs: 6, sm: 6, md: 4, lg: 3 }}>
              <Card
                component={Link}
                to={`/athletes/${formatUrlName(a.name)}`}
                sx={{
                  height: "100%",
                  
                  textDecoration: "none",
                  borderRadius: 3,
                  overflow: "hidden",
                  ":hover": { transform: "translateY(-3px)" },
                  transition: "0.2s",
                }}
              >
                <Box sx={{ position: "relative", pt: "56.25%", bgcolor: "action.hover", height: { xs: '300px', sm:"370px" } }}>
                  {a.photo && (
                    <CardMedia
                      component="img"
                      src={toImageSrc(a.photo)}
                      alt={a.name}
                      sx={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        objectFit: "contain",
                      }}
                      onError={(e) => (e.currentTarget.style.display = "none")}
                    />
                  )}
                </Box>
                <CardContent sx={{ pb: 2 }}>
                  <Typography align="center" variant="subtitle1" noWrap title={a.name}>
                    {a.name}
                  </Typography>
                  <Typography align="center" variant="body2" color="text.secondary" noWrap>
                    {a.country || "—"}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Stack>
  );
}

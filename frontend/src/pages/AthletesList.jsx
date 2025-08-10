import React, { useMemo, useState } from "react";
import {
  Autocomplete,
  TextField,
  Grid,
  Card,
  CardContent,
  Typography,
  CardMedia,
  Box,
  Stack,
  Chip,
} from "@mui/material";
import { Link } from "react-router-dom";
import {
  athletes,
  athleteNames,
  countries,
} from "../helpers/athletes_and_countries";

const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";
const toImageSrc = (photo) => {
  if (!photo) return "";
  return photo.startsWith("http") ? photo : `${apiBase}/media/${photo}`;
};

export default function AthletesList() {
  const [nameQuery, setNameQuery] = useState("");
  const [countryQuery, setCountryQuery] = useState("");
  const [genderQuery, setGenderQuery] = useState("");

  const genders = useMemo(
    () => Array.from(new Set(athletes.map((a) => a.gender).filter(Boolean))),
    []
  );

  const filtered = useMemo(() => {
    const nq = nameQuery.trim().toLowerCase();
    const cq = countryQuery.trim().toLowerCase();
    const gq = genderQuery.trim().toLowerCase();

    return athletes.filter((a) => {
      const matchName = !nq || a.name.toLowerCase().includes(nq);
      const matchCountry = !cq || (a.country || "").toLowerCase().includes(cq);
      const matchGender = !gq || (a.gender || "").toLowerCase() === gq;
      return matchName && matchCountry && matchGender;
    });
  }, [nameQuery, countryQuery, genderQuery]);

  const formatUrlName = (name) =>
    encodeURIComponent(name.replace(/\s+/g, "_"));

  return (
    <Stack spacing={2} sx={{ mb: 4 }}>
      <Typography variant="h4" sx={{textAlign: "center"}}>Athletes</Typography>

      {/* Filters */}
      <Grid container spacing={2} justifyContent={"center"} sx={{textAlign: "center"}}>
        <Grid item size={{ xs: 12, sm: 4 }} >
          <Autocomplete
            
            freeSolo
            options={athleteNames}
            value={null}
            inputValue={nameQuery}
            onInputChange={(_, val) => setNameQuery(val)}
            onChange={(_, val) => setNameQuery(val || "")}
            filterOptions={(x) => x}
            renderInput={(params) => (
              <TextField {...params} label="Search by name" size="small" />
            )}
          />
        </Grid>
        <Grid item size={{ xs: 12, sm: 4 }} >
          <Autocomplete
            fullWidth
            freeSolo
            options={countries}
            value={null}
            inputValue={countryQuery}
            onInputChange={(_, val) => setCountryQuery(val)}
            onChange={(_, val) => setCountryQuery(val || "")}
            filterOptions={(x) => x}
            renderInput={(params) => (
              <TextField {...params} label="Search by country" size="small" />
            )}
          />
        </Grid>
        <Grid item size={{ xs: 12, sm: 4 }} >
          <Autocomplete
            fullWidth
            options={genders}
            
            value={genderQuery || null}
            onChange={(_, val) => setGenderQuery(val || "")}
            renderInput={(params) => (
              <TextField {...params} label="Filter by gender" size="small" textTransform="capitalize" />
            )}
          />
        </Grid>
      </Grid>

      {/* Cards */}
      <Grid container spacing={3}>
        {filtered.map((a) => (
          <Grid key={a.name} item size={{ xs: 6, sm: 6, md: 4, lg: 3 }} >
            <Card
              component={Link}
              to={`/athletes/${formatUrlName(a.name)}`}
              sx={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                textDecoration: "none",
              }}
            >
              {/* Image */}
              <Box sx={{ position: "relative", pt: "56.25%", minHeight: "350px" }}>
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
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                )}
              </Box>

              {/* Content */}
              <CardContent sx={{ flexGrow: 1 }}>
                
                <Typography variant="h6" noWrap title={a.name} align="center">
                  {a.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" align="center">
                  {a.country || "—"}
                </Typography>
                <Box sx={{ display: "flex", justifyContent: "center"}}>
                  
                {a.gender && (
                  <Chip
                    label={a.gender}
                    size="small"
                    
                    sx={{ mt: 1, textTransform: "capitalize", textAlign: "center" }}
                  />
                )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {filtered.length === 0 && (
          <Grid item xs={12}>
            <Typography variant="body2">No athletes found.</Typography>
          </Grid>
        )}
      </Grid>
    </Stack>
  );
}

import client from "./client";

export const fetchAthletes = async ({q="", country=""} = {}) => {
    const response = await client.get("/athletes", {
        params: {q, country}
    });
    return response.data;
};

export const fetchAthlete = async (name) => {
    const response = await client.get(`/athletes/${encodeURIComponent(name)}`);
    return response.data;   
};

export const fetchAllAthletes = async () => {
  const r = await client.get("/athletes/"); // no filters -> all
  return r.data.results || [];
};

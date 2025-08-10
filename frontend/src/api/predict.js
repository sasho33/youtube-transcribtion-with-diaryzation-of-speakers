import client from "./client";

export const postPrediction = async (payload) => {
  const r = await client.post("/predict/", payload);
  return r.data; // { probability, csv_saved_at }
};

import client from "./client";

export const fetchEvents = async (source) => {
  // source optional: "evw" | "kott" | undefined
  if (source === "evw") {
    const r = await client.get("/events/evw");
    return r.data;
  }
  if (source === "kott") {
    const r = await client.get("/events/kott");
    return r.data;
  }
  const r = await client.get("/events/");
  return r.data; // { count, results }
};

export const fetchEventByTitle = async (source, title) => {
  const r = await client.get(`/events/${source}/${encodeURIComponent(title)}`);
  return r.data;
};

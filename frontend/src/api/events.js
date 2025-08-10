// src/api/events.js
import client from "./client";
const API_BASE = import.meta.env.VITE_API_BASE 

// use path segment (evw | kott) — empty for all
export const fetchEvents = async (source) => {
  const path = source ? `/events/${source}` : "/events";
  const r = await client.get(path);
  return r.data; // { count, results }
};
export async function fetchEventByTitle(title) {
  const r = await fetch(`${API_BASE}/events/title?title=${encodeURIComponent(title)}`);
  if (!r.ok) throw new Error(`Event not found (${r.status})`);
  return await r.json();
}

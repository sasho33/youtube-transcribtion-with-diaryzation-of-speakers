// src/api/events.js
import client from "./client";

// use path segment (evw | kott) — empty for all
export const fetchEvents = async (source) => {
  const path = source ? `/events/${source}` : "/events";
  const r = await client.get(path);
  return r.data; // { count, results }
};

// Fixed: Use the dedicated endpoint that matches your Flask route
export async function fetchEventByTitle(source, title) {
  // Use the /events/<source>/<event_title> endpoint
  const encodedTitle = encodeURIComponent(title);
  const url = `${import.meta.env.VITE_API_BASE}/events/${source}/${encodedTitle}`;
  
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch event: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Alternative: If you prefer to use the query parameter approach
export async function fetchEventByTitleAlt(source, title) {
  const url = new URL("/events", import.meta.env.VITE_API_BASE);
  url.searchParams.set("source", source);
  url.searchParams.set("title", title);

  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`Failed to fetch event: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
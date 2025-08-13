// src/api/predictMatch.js
const apiBase = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";

export async function fetchModelPrediction(eventTitle, athlete1, athlete2, opts = {}) {
  const body = {
    event_title: eventTitle,
    athlete1,
    athlete2,
    // Optional knobs with sensible defaults; override via opts if needed
    margin: opts.margin ?? 0.85,
    min_odds: opts.min_odds ?? 1.1,
    max_odds: opts.max_odds ?? 10.0,
  };

  const res = await fetch(`${apiBase}/predict-match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Model prediction failed with ${res.status}`);
  }
  return res.json();
}

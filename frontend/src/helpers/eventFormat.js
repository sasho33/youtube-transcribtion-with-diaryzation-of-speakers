// src/helpers/eventFormat.js
export const toSlug = (s) => encodeURIComponent(s.replace(/\s+/g, "_"));
export const fromSlug = (slug) => decodeURIComponent(slug).replace(/_/g, " ");

// src/helpers/eventFormat.js
export const eventLabel = (title) => {
  const t = title.toLowerCase();
  const numDigits = (title.match(/\d+/) || [null])[0];
  const numRoman = (title.match(/\b[IVXLCDM]+\b/i) || [null])[0];
  const num = numDigits || numRoman || "";
  if (t.includes("east vs west")) return `EvW ${num}`.trim();
  if (t.includes("king of the table")) return `KOTT ${num}`.trim();
  return title;
};


// deterministic bright color from text
export const colorFromText = (text) => {
  const palette = [
    "#7C4DFF","#00BFA5","#F50057","#3D5AFE","#FF6D00",
    "#00C853","#D500F9","#0091EA","#FF3D00","#C51162",
  ];
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = text.charCodeAt(i) + ((hash << 5) - hash);
    hash |= 0;
  }
  const idx = Math.abs(hash) % palette.length;
  return palette[idx];
};

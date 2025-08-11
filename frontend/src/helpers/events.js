// src/helpers/events.js
export function sourceFromTitle(title) {
  // Determine source based on event title patterns
  const lowerTitle = title.toLowerCase();
  
  if (lowerTitle.includes('east vs west') || lowerTitle.includes('evw')) {
    return 'evw';
  }
  
  if (lowerTitle.includes('king of the table') || lowerTitle.includes('kott')) {
    return 'kott';
  }
  
  // Default fallback - you might want to handle this differently
  return 'evw';
}
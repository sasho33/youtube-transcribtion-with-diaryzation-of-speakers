export function sourceFromTitle(title) {
  if (/^east vs west/i.test(title)) return 'evw';
  if (/^king of the table/i.test(title)) return 'kott';
  return 'evw'; // default/fallback if you want
}
export const pctFormatter = (value: number | null ) : string  => {
  if (value == null) return 'N/A';
  const percentageValue = value < 0 ? -value * 100 : value * 100;
  return `${Number(percentageValue.toFixed(1)).toString()}%`;
}

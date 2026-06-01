import { formatCurrency, formatTooltipValue } from "../utils/dashboard";

export function ChartTooltip({ active, payload, label, currency = false }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="tooltip-row">
          <span>{entry.name || entry.dataKey}</span>
          <span>
            {currency ? formatCurrency(entry.value) : formatTooltipValue(entry.dataKey, entry.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

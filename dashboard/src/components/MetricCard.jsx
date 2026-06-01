export function MetricCard({ label, value, detail, highlight = false }) {
  return (
    <div className={`metric-card ${highlight ? "highlight" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </div>
  );
}

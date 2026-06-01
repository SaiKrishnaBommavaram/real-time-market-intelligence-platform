export function buildMarketMetrics(rows) {
  if (!rows.length) {
    return {
      tickerCount: 0,
      dayCount: 0,
      totalVolume: 0,
      avgPrice: 0,
    };
  }

  const tickerCount = new Set(rows.map((row) => row.ticker)).size;
  const dayCount = new Set(rows.map((row) => row.trade_date)).size;
  const totalVolume = rows.reduce(
    (sum, row) => sum + Number(row.total_volume || 0),
    0,
  );
  const avgPrice =
    rows.reduce((sum, row) => sum + Number(row.avg_price || 0), 0) / rows.length;

  return { tickerCount, dayCount, totalVolume, avgPrice };
}

export function buildMarketTrend(rows) {
  const grouped = rows.reduce((acc, row) => {
    const date = row.trade_date;
    if (!acc[date]) {
      acc[date] = {
        tradeDate: date,
        rawDate: new Date(date).getTime(),
        totalVolume: 0,
        avgPriceSum: 0,
        count: 0,
      };
    }

    acc[date].totalVolume += Number(row.total_volume || 0);
    acc[date].avgPriceSum += Number(row.avg_price || 0);
    acc[date].count += 1;
    return acc;
  }, {});

  return Object.values(grouped)
    .sort((a, b) => a.rawDate - b.rawDate)
    .map((row) => ({
      tradeDate: shortDate(row.tradeDate),
      totalVolume: row.totalVolume,
      avgPrice: Number((row.avgPriceSum / row.count).toFixed(2)),
    }));
}

export function buildMarketLeaders(rows) {
  const latestByTicker = rows.reduce((acc, row) => {
    const current = acc[row.ticker];
    if (!current || new Date(row.trade_date) > new Date(current.trade_date)) {
      acc[row.ticker] = row;
    }
    return acc;
  }, {});

  return Object.values(latestByTicker)
    .sort((a, b) => Number(b.total_volume || 0) - Number(a.total_volume || 0))
    .slice(0, 6);
}

export function buildTickerTrend(rows) {
  return [...rows]
    .map((row) => ({
      tradeDate: shortDate(row.trade_date),
      avgPrice: Number(row.avg_price || 0),
    }))
    .reverse();
}

export function formatInteger(value) {
  return Number(value || 0).toLocaleString();
}

export function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value || 0));
}

export function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

export function formatDate(value) {
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function shortDate(value) {
  const date = new Date(value);
  return `${date.toLocaleDateString("en-US", { month: "short" })} ${date.getDate()}`;
}

export function formatTimestamp(value) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatTooltipValue(key, value) {
  if (key?.toLowerCase().includes("price")) {
    return formatCurrency(value);
  }

  return formatCompactNumber(value);
}

export function getSentimentClass(score) {
  if (score > 0.2) return "positive";
  if (score < -0.2) return "negative";
  return "neutral";
}

export function getSentimentLabel(score) {
  if (score > 0.2) return "Positive";
  if (score < -0.2) return "Negative";
  return "Neutral";
}

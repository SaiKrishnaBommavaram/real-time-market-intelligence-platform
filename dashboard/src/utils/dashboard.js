export const DEFAULT_PRICE_ALERT_THRESHOLD = 4;
export const DEFAULT_VOLUME_ALERT_THRESHOLD = 1.5;

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

export function getLatestSummaryByTicker(rows) {
  return rows.reduce((acc, row) => {
    const current = acc[row.ticker];
    if (!current || new Date(row.trade_date) > new Date(current.trade_date)) {
      acc[row.ticker] = row;
    }
    return acc;
  }, {});
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
  return Object.values(getLatestSummaryByTicker(rows))
    .sort((a, b) => Number(b.total_volume || 0) - Number(a.total_volume || 0))
    .slice(0, 6);
}

export function buildTopMovers(rows) {
  return Object.values(getLatestSummaryByTicker(rows))
    .sort(
      (a, b) =>
        Math.abs(Number(b.price_change_pct || 0)) -
        Math.abs(Number(a.price_change_pct || 0)),
    )
    .slice(0, 6);
}

export function buildAnomalyFeed(rows) {
  return Object.values(getLatestSummaryByTicker(rows))
    .filter((row) => isAnomalousRow(row))
    .sort((a, b) => {
      const aSeverity =
        Math.abs(Number(a.price_change_pct || 0)) + Number(a.volume_vs_avg_ratio || 0);
      const bSeverity =
        Math.abs(Number(b.price_change_pct || 0)) + Number(b.volume_vs_avg_ratio || 0);
      return bSeverity - aSeverity;
    })
    .slice(0, 8);
}

export function buildTickerTrend(rows) {
  return [...rows]
    .map((row) => ({
      tradeDate: shortDate(row.trade_date),
      avgPrice: Number(row.avg_price || 0),
      closePrice: Number(row.close_price || row.avg_price || 0),
    }))
    .reverse();
}

export function createWatchlistEntry(ticker) {
  return {
    ticker,
    priceAlertThreshold: DEFAULT_PRICE_ALERT_THRESHOLD,
    volumeAlertThreshold: DEFAULT_VOLUME_ALERT_THRESHOLD,
  };
}

export function buildWatchlistEntries(rows, watchlist) {
  const latestByTicker = getLatestSummaryByTicker(rows);

  return watchlist.map((item) => {
    const summary = latestByTicker[item.ticker];
    const priceChange = Number(summary?.price_change_pct || 0);
    const volumeRatio = Number(summary?.volume_vs_avg_ratio || 1);
    const priceAlertTriggered = Math.abs(priceChange) >= Number(item.priceAlertThreshold);
    const volumeAlertTriggered = volumeRatio >= Number(item.volumeAlertThreshold);

    return {
      ...item,
      summary,
      priceAlertTriggered,
      volumeAlertTriggered,
      hasAlert: priceAlertTriggered || volumeAlertTriggered || isAnomalousRow(summary),
    };
  });
}

export function isAnomalousRow(row) {
  if (!row) {
    return false;
  }

  return row.anomaly_flag && row.anomaly_flag !== "normal";
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

export function formatPercent(value) {
  const numericValue = Number(value || 0);
  return `${numericValue >= 0 ? "+" : ""}${numericValue.toFixed(2)}%`;
}

export function formatRatio(value) {
  return `${Number(value || 0).toFixed(2)}x`;
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

export function getPriceChangeClass(value) {
  const numericValue = Number(value || 0);
  if (numericValue > 0.25) return "positive";
  if (numericValue < -0.25) return "negative";
  return "neutral";
}

export function getAnomalyLabel(flag) {
  switch (flag) {
    case "price_and_volume":
      return "Price + volume anomaly";
    case "price_move":
      return "Large price move";
    case "volume_spike":
      return "Volume spike";
    default:
      return "Normal";
  }
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

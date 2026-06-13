import axios from "axios";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const configuredApiKey = import.meta.env.VITE_API_KEY;
const API_VERSION_PREFIX = "/v1";
const isLocalHost =
  typeof window !== "undefined" &&
  ["localhost", "127.0.0.1"].includes(window.location.hostname);

const API_BASE_URL = configuredApiBaseUrl || (isLocalHost ? "http://localhost:8000" : null);
const apiClient = axios.create();

if (configuredApiKey) {
  apiClient.defaults.headers.common["x-api-key"] = configuredApiKey;
}

function getApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error(
      "VITE_API_BASE_URL is not configured for this deployed frontend.",
    );
  }

  return API_BASE_URL;
}

function getApiRoot() {
  return `${getApiBaseUrl()}${API_VERSION_PREFIX}`;
}

export async function fetchHealth() {
  const response = await apiClient.get(`${getApiRoot()}/health`);
  return response.data;
}

export async function fetchMarketSummary() {
  const response = await apiClient.get(`${getApiRoot()}/market/summary`);
  return response.data;
}

export async function fetchLiveStock(ticker) {
  const response = await apiClient.get(`${getApiRoot()}/stocks/${ticker}/live`);
  return response.data;
}

export async function fetchStockSummary(ticker) {
  const response = await apiClient.get(`${getApiRoot()}/stocks/${ticker}/summary`);
  return response.data;
}

export async function fetchStockNews(ticker) {
  const response = await apiClient.get(`${getApiRoot()}/stocks/${ticker}/news`);
  return response.data;
}

export async function fetchStockNewsSummary(ticker) {
  const response = await apiClient.get(
    `${getApiRoot()}/stocks/${ticker}/news/summary`,
  );
  return response.data;
}

export async function fetchWatchlist() {
  const response = await apiClient.get(`${getApiRoot()}/watchlist`);
  return response.data;
}

export async function upsertWatchlistItem(payload) {
  const response = await apiClient.post(`${getApiRoot()}/watchlist`, payload);
  return response.data;
}

export async function deleteWatchlistItem(ticker) {
  const response = await apiClient.delete(`${getApiRoot()}/watchlist/${ticker}`);
  return response.data;
}

export async function fetchIntradayMovers() {
  const response = await apiClient.get(`${getApiRoot()}/analytics/intraday/movers`);
  return response.data;
}

export async function fetchIntradayCandles(ticker) {
  const response = await apiClient.get(`${getApiRoot()}/analytics/intraday/${ticker}`);
  return response.data;
}

export async function fetchWatchlistAlerts() {
  const response = await apiClient.get(`${getApiRoot()}/watchlist/alerts`);
  return response.data;
}

export async function fetchAnomalyHistory(limit = 120) {
  const response = await apiClient.get(`${getApiRoot()}/analytics/anomalies`, {
    params: { limit },
  });
  return response.data;
}

export async function fetchObservabilityMetrics() {
  const response = await apiClient.get(`${getApiRoot()}/observability/metrics`);
  return response.data;
}

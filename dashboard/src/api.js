import axios from "axios";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const isLocalHost =
  typeof window !== "undefined" &&
  ["localhost", "127.0.0.1"].includes(window.location.hostname);

const API_BASE_URL = configuredApiBaseUrl || (isLocalHost ? "http://localhost:8000" : null);

function getApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error(
      "VITE_API_BASE_URL is not configured for this deployed frontend.",
    );
  }

  return API_BASE_URL;
}

export async function fetchHealth() {
  const response = await axios.get(`${getApiBaseUrl()}/health`);
  return response.data;
}

export async function fetchMarketSummary() {
  const response = await axios.get(`${getApiBaseUrl()}/market/summary`);
  return response.data;
}

export async function fetchLiveStock(ticker) {
  const response = await axios.get(`${getApiBaseUrl()}/stocks/${ticker}/live`);
  return response.data;
}

export async function fetchStockSummary(ticker) {
  const response = await axios.get(`${getApiBaseUrl()}/stocks/${ticker}/summary`);
  return response.data;
}

export async function fetchStockNews(ticker) {
  const response = await axios.get(`${getApiBaseUrl()}/stocks/${ticker}/news`);
  return response.data;
}

export async function fetchStockNewsSummary(ticker) {
  const response = await axios.get(
    `${getApiBaseUrl()}/stocks/${ticker}/news/summary`,
  );
  return response.data;
}

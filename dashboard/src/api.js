import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

export async function fetchHealth() {
  const response = await axios.get(`${API_BASE_URL}/health`);
  return response.data;
}

export async function fetchMarketSummary() {
  const response = await axios.get(`${API_BASE_URL}/market/summary`);
  return response.data;
}

export async function fetchLiveStock(ticker) {
  const response = await axios.get(`${API_BASE_URL}/stocks/${ticker}/live`);
  return response.data;
}

export async function fetchStockNews(ticker) {
  const response = await axios.get(`${API_BASE_URL}/stocks/${ticker}/news`);
  return response.data;
}

export async function fetchStockNewsSummary(ticker) {
  const response = await axios.get(
    `${API_BASE_URL}/stocks/${ticker}/news/summary`,
  );
  return response.data;
}

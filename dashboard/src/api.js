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

export async function fetchStockSummary(ticker) {
  const response = await axios.get(`${API_BASE_URL}/stocks/${ticker}/summary`);
  return response.data;
}
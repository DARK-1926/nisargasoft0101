import type {
  AlertEvent,
  CurrentAsin,
  DiscoverProductsResponse,
  HistoryResponse,
  LocationProfile,
  MarketInsight,
  ProductSummary,
  TrackUrlResponse,
  WatchlistItem,
} from "./types";

const host = window.location.hostname || "127.0.0.1";
const LOCAL_API_BASE = `${window.location.protocol}//${host}:8000/api`;
const useDirectLocalApi =
  import.meta.env.DEV || ["3000", "4173", "5173"].includes(window.location.port);
const API_BASE = import.meta.env.VITE_API_BASE_URL?.trim() || (useDirectLocalApi ? LOCAL_API_BASE : "/api");

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the generic status message when the server does not return JSON.
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  return parseResponse<T>(response);
}

async function postJson<T, B>(path: string, body: B): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export function getProducts(): Promise<ProductSummary[]> {
  return fetchJson<ProductSummary[]>("/products");
}

export function getLocations(): Promise<LocationProfile[]> {
  return fetchJson<LocationProfile[]>("/locations");
}

export function getCurrent(asin: string, locationCode: string): Promise<CurrentAsin> {
  return fetchJson<CurrentAsin>(`/current/${asin}?location_code=${encodeURIComponent(locationCode)}`);
}

export function getHistory(asin: string, locationCode: string, hours = 168): Promise<HistoryResponse> {
  return fetchJson<HistoryResponse>(
    `/history/${asin}?location_code=${encodeURIComponent(locationCode)}&hours=${hours}`,
  );
}

export function getInsights(asin: string, locationCode: string, hours = 168): Promise<MarketInsight> {
  return fetchJson<MarketInsight>(
    `/insights/${asin}?location_code=${encodeURIComponent(locationCode)}&hours=${hours}`,
  );
}

export function getAlerts(): Promise<AlertEvent[]> {
  return fetchJson<AlertEvent[]>("/alerts");
}

export function trackAmazonUrl(url: string, locationCode: string, titleHint?: string): Promise<TrackUrlResponse> {
  return postJson<TrackUrlResponse, { url: string; location_code: string; title_hint?: string }>("/track-url", {
    url,
    location_code: locationCode,
    title_hint: titleHint,
  });
}

export function discoverProducts(
  query: string,
  locationCode: string,
  brandFilter?: string,
  modelFilter?: string,
  maxPages = 1,
): Promise<DiscoverProductsResponse> {
  return postJson<
    DiscoverProductsResponse,
    {
      query: string;
      location_code: string;
      max_pages: number;
      brand_filter?: string;
      model_filter?: string;
    }
  >(
    "/discover",
    {
      query,
      location_code: locationCode,
      max_pages: maxPages,
      brand_filter: brandFilter,
      model_filter: modelFilter,
    },
  );
}

export function getWatchlist(locationCode?: string): Promise<WatchlistItem[]> {
  const suffix = locationCode ? `?location_code=${encodeURIComponent(locationCode)}` : "";
  return fetchJson<WatchlistItem[]>(`/watchlist${suffix}`);
}

export function addWatchlistItem(payload: {
  asin: string;
  title?: string;
  brand?: string | null;
  location_code: string;
  source_query?: string;
  brand_filter?: string;
  model_filter?: string;
}): Promise<WatchlistItem> {
  return postJson<WatchlistItem, typeof payload>("/watchlist", payload);
}

export async function removeWatchlistItem(asin: string, locationCode: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/watchlist/${encodeURIComponent(asin)}?location_code=${encodeURIComponent(locationCode)}`,
    { method: "DELETE" },
  );
  await parseResponse<{ deleted: boolean }>(response);
}

export const streamUrl = `${API_BASE}/stream`;

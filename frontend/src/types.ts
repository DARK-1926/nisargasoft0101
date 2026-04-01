export type ProductSummary = {
  asin: string;
  title: string;
  brand: string | null;
  last_seen_at: string | null;
  available_locations: string[];
};

export type LocationProfile = {
  code: string;
  city: string;
  state: string;
  pin_code: string;
};

export type CurrentOffer = {
  seller_id: string;
  seller_name: string;
  price: number;
  list_price: number | null;
  shipping_price: number | null;
  availability: string | null;
  fba_status: boolean;
  buy_box_flag: boolean;
  is_prime: boolean;
  offer_url: string | null;
  captured_at: string;
};

export type CurrentAsin = {
  asin: string;
  title: string;
  location_code: string;
  captured_at: string | null;
  buy_box_offer: CurrentOffer | null;
  offers: CurrentOffer[];
};

export type HistoryPoint = {
  captured_at: string;
  price: number;
  buy_box_flag: boolean;
};

export type HistorySeries = {
  seller_id: string;
  seller_name: string;
  points: HistoryPoint[];
};

export type HistoryResponse = {
  asin: string;
  location_code: string;
  hours: number;
  series: HistorySeries[];
};

export type SellerInsight = {
  seller_id: string;
  seller_name: string;
  min_price: number;
  max_price: number;
  avg_price: number;
  latest_price: number;
  price_change_count: number;
  buy_box_wins: number;
  leadership_wins: number;
};

export type MarketInsight = {
  asin: string;
  title: string;
  location_code: string;
  hours: number;
  snapshot_count: number;
  seller_count: number;
  captured_from: string | null;
  captured_to: string | null;
  current_lowest_price: number | null;
  current_lowest_seller: string | null;
  buy_box_seller: string | null;
  highest_price_seen: number | null;
  lowest_price_seen: number | null;
  seller_insights: SellerInsight[];
};

export type AlertEvent = {
  id: string;
  asin: string;
  product_title: string;
  location_code: string;
  competitor_seller_name: string;
  own_seller_name: string;
  competitor_price: number;
  own_price: number;
  delta_percent: number;
  message: string;
  slack_sent: boolean;
  email_sent: boolean;
  created_at: string;
};

export type TrackUrlResponse = {
  asin: string;
  location_code: string;
  product: ProductSummary;
  snapshot: CurrentAsin;
};

export type DiscoverProductsResponse = {
  query: string;
  location_code: string;
  brand_filter: string | null;
  model_filter: string | null;
  tracked_count: number;
  products: ProductSummary[];
};

export type WatchlistItem = {
  id: string;
  asin: string;
  title: string;
  brand: string | null;
  location_code: string;
  source_query: string | null;
  brand_filter: string | null;
  model_filter: string | null;
  last_seen_at: string | null;
  created_at: string;
};

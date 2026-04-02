import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  addWatchlistItem,
  ApiError,
  discoverProducts,
  getCurrent,
  getLocations,
  getWatchlist,
  removeWatchlistItem,
  trackAmazonUrl,
} from "./api";
import type { CurrentAsin, LocationProfile, ProductSummary, WatchlistItem } from "./types";

function formatPrice(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "N/A";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "No snapshot yet";
  }
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function locationLabel(location: LocationProfile | null) {
  if (!location) {
    return "Choose location";
  }
  return `${location.city}, ${location.state} (${location.pin_code})`;
}

export default function App() {
  const queryClient = useQueryClient();
  const [productUrl, setProductUrl] = useState("");
  const [discoverQueryInput, setDiscoverQueryInput] = useState("");
  const [brandFilterInput, setBrandFilterInput] = useState("");
  const [modelFilterInput, setModelFilterInput] = useState("");
  const [selectedLocation, setSelectedLocation] = useState("");
  const [selectedAsin, setSelectedAsin] = useState("");
  const [discoveredProducts, setDiscoveredProducts] = useState<ProductSummary[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const locationsQuery = useQuery({
    queryKey: ["locations"],
    queryFn: getLocations,
  });
  const watchlistQuery = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => getWatchlist(),
    refetchInterval: 60_000,
  });
  const currentQuery = useQuery({
    queryKey: ["current", selectedAsin, selectedLocation],
    queryFn: () => getCurrent(selectedAsin, selectedLocation),
    enabled: Boolean(selectedAsin && selectedLocation),
    refetchInterval: 60_000,
  });

  useEffect(() => {
    if (!selectedLocation && locationsQuery.data?.length) {
      setSelectedLocation(locationsQuery.data[0].code);
    }
  }, [locationsQuery.data, selectedLocation]);

  useEffect(() => {
    if (!selectedAsin && watchlistQuery.data?.length) {
      setSelectedAsin(watchlistQuery.data[0].asin);
      setSelectedLocation(watchlistQuery.data[0].location_code);
    }
  }, [watchlistQuery.data, selectedAsin]);

  const location = locationsQuery.data?.find((item) => item.code === selectedLocation) ?? null;
  const snapshot: CurrentAsin | null = currentQuery.data ?? null;
  const watchlist = watchlistQuery.data ?? [];
  const selectedWatchlistItem =
    watchlist.find((item) => item.asin === selectedAsin && item.location_code === selectedLocation) ?? null;
  const watchlistKeys = new Set(watchlist.map((item) => `${item.asin}:${item.location_code}`));

  const trackMutation = useMutation({
    mutationFn: async () => trackAmazonUrl(productUrl.trim(), selectedLocation),
    onSuccess: async (result) => {
      setStatusMessage(`Tracked ${result.asin} for ${locationLabel(location)}.`);
      setProductUrl("");
      setSelectedAsin(result.asin);
      await queryClient.invalidateQueries({ queryKey: ["current", result.asin, selectedLocation] });
    },
  });

  const discoverMutation = useMutation({
    mutationFn: async () =>
      discoverProducts(
        discoverQueryInput.trim(),
        selectedLocation,
        brandFilterInput.trim() || undefined,
        modelFilterInput.trim() || undefined,
        1,
      ),
    onSuccess: (result) => {
      setDiscoveredProducts(result.products);
      setStatusMessage(
        result.products.length
          ? `Found ${result.products.length} products for "${result.query}".`
          : `No products found for "${result.query}".`,
      );
    },
  });

  const addMutation = useMutation({
    mutationFn: async (payload: {
      asin: string;
      title?: string;
      brand?: string | null;
      locationCode: string;
      sourceQuery?: string;
      brandFilter?: string;
      modelFilter?: string;
    }) =>
      addWatchlistItem({
        asin: payload.asin,
        title: payload.title,
        brand: payload.brand,
        location_code: payload.locationCode,
        source_query: payload.sourceQuery,
        brand_filter: payload.brandFilter,
        model_filter: payload.modelFilter,
      }),
    onSuccess: async (item) => {
      setStatusMessage(`Added ${item.asin} to the watchlist for ${item.location_code}.`);
      setSelectedAsin(item.asin);
      setSelectedLocation(item.location_code);
      await queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: async (payload: { asin: string; locationCode: string }) =>
      removeWatchlistItem(payload.asin, payload.locationCode),
    onSuccess: async () => {
      setStatusMessage("Removed product from the watchlist.");
      await queryClient.invalidateQueries({ queryKey: ["watchlist"] });
      if (selectedWatchlistItem) {
        const remaining = (queryClient.getQueryData<WatchlistItem[]>(["watchlist"]) ?? []).filter(
          (item) => !(item.asin === selectedWatchlistItem.asin && item.location_code === selectedWatchlistItem.location_code),
        );
        if (remaining[0]) {
          setSelectedAsin(remaining[0].asin);
          setSelectedLocation(remaining[0].location_code);
        }
      }
    },
  });

  const mutationError =
    (trackMutation.error instanceof ApiError ? trackMutation.error.message : null) ??
    (discoverMutation.error instanceof ApiError ? discoverMutation.error.message : null) ??
    (addMutation.error instanceof ApiError ? addMutation.error.message : null) ??
    (removeMutation.error instanceof ApiError ? removeMutation.error.message : null);
  const actionBusy =
    trackMutation.isPending ||
    discoverMutation.isPending ||
    addMutation.isPending ||
    removeMutation.isPending;

  const currentProductInWatchlist = selectedAsin ? watchlistKeys.has(`${selectedAsin}:${selectedLocation}`) : false;
  const currentError = currentQuery.error instanceof ApiError ? currentQuery.error.message : null;
  const trackedCandidates = useMemo(
    () =>
      discoveredProducts.map((product) => ({
        ...product,
        inWatchlist: watchlistKeys.has(`${product.asin}:${selectedLocation}`),
      })),
    [discoveredProducts, selectedLocation, watchlistKeys],
  );

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Amazon India Price Monitor</p>
        <h1>Track any Amazon product and monitor competitor pricing.</h1>
        <p className="intro">
          Paste any Amazon product URL to start tracking, search for products by query,
          add ASINs to the watchlist, and inspect the current seller stack and Buy Box per buyer location.
        </p>
      </section>

      <section className="tracker-card">
        <div className="form-grid quad">
          <div className="field">
            <label htmlFor="discover-query">Search query</label>
            <input
              id="discover-query"
              value={discoverQueryInput}
              onChange={(event) => setDiscoverQueryInput(event.target.value)}
              placeholder="e.g. SKF bearing 6205, iPhone 15, boAt headphones"
            />
          </div>
          <div className="field">
            <label htmlFor="brand-filter">Brand filter</label>
            <input
              id="brand-filter"
              value={brandFilterInput}
              onChange={(event) => setBrandFilterInput(event.target.value)}
              placeholder="Optional brand filter"
            />
          </div>
          <div className="field">
            <label htmlFor="model-filter">Model filter</label>
            <input
              id="model-filter"
              value={modelFilterInput}
              onChange={(event) => setModelFilterInput(event.target.value)}
              placeholder="Optional model filter"
            />
          </div>
          <div className="field">
            <label htmlFor="buyer-location">Buyer location</label>
            <select
              id="buyer-location"
              value={selectedLocation}
              onChange={(event) => setSelectedLocation(event.target.value)}
            >
              {(locationsQuery.data ?? []).map((item) => (
                <option key={item.code} value={item.code}>
                  {item.city}, {item.state} ({item.pin_code})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-grid duo lower-gap">
          <div className="field">
            <label htmlFor="product-url">Track one Amazon product URL directly</label>
            <input
              id="product-url"
              value={productUrl}
              onChange={(event) => setProductUrl(event.target.value)}
              placeholder="https://www.amazon.in/dp/<ASIN>"
            />
          </div>
        </div>

        <div className="action-row wrap">
          <button
            type="button"
            className="secondary-button"
            disabled={!discoverQueryInput.trim() || !selectedLocation || actionBusy}
            onClick={() => {
              setStatusMessage(`Searching "${discoverQueryInput.trim()}" in ${locationLabel(location)}.`);
              discoverMutation.mutate();
            }}
          >
            {discoverMutation.isPending ? "Discovering..." : "Discover Products"}
          </button>
          <button
            type="button"
            className="primary-button"
            disabled={!productUrl.trim() || !selectedLocation || actionBusy}
            onClick={() => {
              setStatusMessage(`Fetching live offers for ${locationLabel(location)}. This can take up to a minute.`);
              trackMutation.mutate();
            }}
          >
            {trackMutation.isPending ? "Fetching..." : "Track Product URL"}
          </button>
          <span className="helper-text">Scheduler monitors all watchlist ASINs automatically.</span>
        </div>

        {actionBusy ? <div className="message info">{statusMessage}</div> : null}
        {!actionBusy && mutationError ? <div className="message error">{mutationError}</div> : null}
        {!actionBusy && !mutationError && statusMessage ? <div className="message success">{statusMessage}</div> : null}
      </section>

      <section className="panels-grid">
        <article className="list-card">
          <div className="section-head">
            <h3>Discovery results</h3>
            <span>{trackedCandidates.length} products</span>
          </div>
          <div className="tracked-list">
            {trackedCandidates.length ? (
              trackedCandidates.map((product) => (
                <div key={product.asin} className="tracked-item static-item">
                  <strong>{product.title}</strong>
                  <span>{product.asin}</span>
                  <small>{product.brand ?? "Unknown brand"}</small>
                  <div className="inline-actions">
                    <button
                      type="button"
                      className="mini-button"
                      disabled={product.inWatchlist || actionBusy}
                      onClick={() =>
                        addMutation.mutate({
                          asin: product.asin,
                          title: product.title,
                          brand: product.brand,
                          locationCode: selectedLocation,
                          sourceQuery: discoverQueryInput.trim(),
                          brandFilter: brandFilterInput.trim() || undefined,
                          modelFilter: modelFilterInput.trim() || undefined,
                        })
                      }
                    >
                      {product.inWatchlist ? "Tracked" : "Add to Watchlist"}
                    </button>
                    <button
                      type="button"
                      className="mini-button ghost"
                      onClick={() => {
                        setSelectedAsin(product.asin);
                      }}
                    >
                      View Snapshot
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-mini">Run a search query to discover products, or paste a URL directly.</div>
            )}
          </div>
        </article>

        <article className="list-card">
          <div className="section-head">
            <h3>Watchlist</h3>
            <span>{watchlist.length} tracked</span>
          </div>
          <div className="tracked-list">
            {watchlist.length ? (
              watchlist.map((item) => (
                <div
                  key={`${item.asin}:${item.location_code}`}
                  className={`tracked-item static-item ${item.asin === selectedAsin && item.location_code === selectedLocation ? "active" : ""}`}
                >
                  <button
                    type="button"
                    className="tracked-select"
                    onClick={() => {
                      setSelectedAsin(item.asin);
                      setSelectedLocation(item.location_code);
                    }}
                  >
                    <strong>{item.title}</strong>
                    <span>{item.asin}</span>
                    <small>
                      {item.location_code} | {formatTimestamp(item.last_seen_at)}
                    </small>
                  </button>
                  <div className="inline-actions">
                    <button
                      type="button"
                      className="mini-button danger"
                      disabled={actionBusy}
                      onClick={() =>
                        removeMutation.mutate({
                          asin: item.asin,
                          locationCode: item.location_code,
                        })
                      }
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-mini">No tracked ASINs yet. Paste a product URL or search to start monitoring.</div>
            )}
          </div>
        </article>
      </section>

      {snapshot ? (
        <section className="results">
          <article className="summary-card">
            <div className="summary-copy">
              <p className="asin">{snapshot.asin}</p>
              <h2>{snapshot.title}</h2>
              <p className="meta">Snapshot: {formatTimestamp(snapshot.captured_at)}</p>
              <p className="meta">Location: {locationLabel(location)}</p>
            </div>

            <div className="summary-stats">
              <div className="stat">
                <span>Buy Box seller</span>
                <strong>{snapshot.buy_box_offer?.seller_name ?? "Unknown"}</strong>
              </div>
              <div className="stat">
                <span>Buy Box price</span>
                <strong>{formatPrice(snapshot.buy_box_offer?.price)}</strong>
              </div>
              <div className="stat">
                <span>Live sellers</span>
                <strong>{snapshot.offers.length}</strong>
              </div>
            </div>
          </article>

          {!currentProductInWatchlist && selectedAsin ? (
            <div className="message info">
              This ASIN is not in the watchlist yet.
              <button
                type="button"
                className="mini-button inline-pad"
                disabled={actionBusy}
                onClick={() =>
                  addMutation.mutate({
                    asin: selectedAsin,
                    title: snapshot.title,
                    locationCode: selectedLocation,
                    sourceQuery: discoverQueryInput.trim() || undefined,
                    brandFilter: brandFilterInput.trim() || undefined,
                    modelFilter: modelFilterInput.trim() || undefined,
                  })
                }
              >
                Add to Watchlist
              </button>
            </div>
          ) : null}

          <article className="buybox-card">
            <p className="section-label">Default Buy Box</p>
            <div className="buybox-row">
              <div>
                <h3>{snapshot.buy_box_offer?.seller_name ?? "Unknown"}</h3>
                <p>{snapshot.buy_box_offer?.availability ?? "Availability unknown"}</p>
              </div>
              <strong>{formatPrice(snapshot.buy_box_offer?.price)}</strong>
            </div>
          </article>

          <article className="offers-card">
            <div className="section-head">
              <h3>Live seller offers</h3>
              <span>{snapshot.offers.length} sellers</span>
            </div>

            <div className="offer-list">
              {snapshot.offers.map((offer, index) => (
                <div key={`${offer.seller_id}-${offer.captured_at}-${index}`} className="offer-row">
                  <div className="offer-rank">{index + 1}</div>
                  <div className="offer-main">
                    <div className="offer-title-row">
                      <strong>{offer.seller_name}</strong>
                      {offer.buy_box_flag ? <span className="pill buybox">Buy Box</span> : null}
                      {offer.fba_status ? <span className="pill">FBA</span> : <span className="pill muted-pill">Merchant</span>}
                    </div>
                    <p>{offer.availability ?? "Availability unknown"}</p>
                  </div>
                  <div className="offer-price">{formatPrice(offer.price)}</div>
                </div>
              ))}
            </div>
          </article>
        </section>
      ) : (
        <section className="empty-panel">
          <h2>No tracked snapshot selected</h2>
          <p>Select a watchlist ASIN or run a direct product tracking request.</p>
          {currentError ? <div className="message error">{currentError}</div> : null}
        </section>
      )}
    </main>
  );
}

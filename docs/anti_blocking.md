# Anti-Blocking Strategy

## Current Controls

- Rotating proxy support through `ROTATING_PROXIES`.
- User-agent rotation in scraper middleware.
- Location-aware `X-Forwarded-For` headers for buyer simulation.
- Playwright rendering for dynamic Amazon surfaces.
- Retry handling for proxy failures.
- Failure artifact capture including HTML, metadata, and screenshots.

## Operating Guidance

- Use a proxy pool with enough geographic diversity and concurrency headroom.
- Keep scraper concurrency conservative until live success rates are measured.
- Review captured artifacts whenever selectors stop matching.
- Separate debugging runs from scheduled runs so selectors can be tuned safely.
- Treat Amazon location simulation as best-effort and validate output manually across important PIN codes.

## Remaining Risks

- Amazon may return different DOM structures, challenges, or seller ordering based on session quality.
- Random proxy rotation alone is weaker than health-scored proxy pools.
- Buy Box detection should be cross-checked with manual browser validation during pilot rollout.

## Recommended Next Hardening Step

- Add proxy health scoring, proxy cooldowns, and scrape success-rate dashboards before scaling up monitored ASIN volume.

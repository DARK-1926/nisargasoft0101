# Update Vercel Environment Variable

Your API is now running on your custom domain with SSL!

## New API URL
`https://api.darkproject.store`

## Steps to Update Vercel

1. Go to your Vercel project: https://vercel.com/dashboard
2. Select the `nisargasoft0101` project
3. Go to **Settings** → **Environment Variables**
4. Find `VITE_API_BASE_URL` and update it to:
   ```
   https://api.darkproject.store/api
   ```
5. Click **Save**
6. Go to **Deployments** tab
7. Click the **...** menu on the latest deployment
8. Click **Redeploy** to apply the new environment variable

## What Changed

- ✅ Custom domain: `api.darkproject.store`
- ✅ SSL/HTTPS enabled with Let's Encrypt
- ✅ Certificates auto-renew every 90 days
- ✅ CORS configured for your frontend
- ✅ 15-minute timeout for scraper requests
- ✅ No more Cloudflare tunnel timeouts
- ✅ Fixed track-url to only scrape requested location (faster)
- ✅ Fixed database schema for long availability text

## Test URLs

- Health check: https://api.darkproject.store/health
- Locations: https://api.darkproject.store/api/locations
- Watchlist: https://api.darkproject.store/api/watchlist
- Alerts: https://api.darkproject.store/api/alerts

## Certificate Renewal

Certbot is configured to automatically renew certificates. The renewal timer runs daily and will renew certificates 30 days before expiration.

Check renewal status:
```bash
sudo certbot renew --dry-run
```

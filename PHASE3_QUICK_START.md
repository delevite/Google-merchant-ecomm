# Phase 3 Quick Start & Testing Guide

## Installation

### Step 1: Install Phase 3 Dependencies
```bash
pip install -r requirements.txt

# Or specifically:
pip install google-cloud-merchant schedule
```

### Step 2: Configure Environment
```bash
# Already created in Phase 1, just verify these are set:
# From .env file:

MERCHANT_API_ENABLED=True
GCP_PROJECT_ID=your-gcp-project-id
GCP_MERCHANT_ID=your-merchant-center-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/gcp-service-account.json
MERCHANT_API_FEED_SYNC_INTERVAL_MINUTES=60
```

### Step 3: Restart Flask App
```bash
python netlify/functions/api/api.py
```

---

## Testing Phase 3

### Quick Test 1: Module Loading
```bash
# Verify Phase 3 module loads
python -c "from src.merchant_api import MerchantAPIClient; print('✓ Phase 3 module loaded')"

# Expected: ✓ Phase 3 module loaded
```

### Quick Test 2: API Endpoint Availability
```bash
# Start Flask app in one terminal
python netlify/functions/api/api.py

# In another terminal, test Phase 3 endpoints:

# Check Phase 3 status
curl http://localhost:5000/api/phase-3-info | jq '.'

# Check sync status
curl http://localhost:5000/api/merchant-sync-status | jq '.'

# Get mock insights
curl http://localhost:5000/api/merchant-insights?days=30 | jq '.metrics'

# Get inventory
curl http://localhost:5000/api/merchant-inventory | jq '.'
```

### Quick Test 3: Trigger Sync
```bash
# Make sure gmc_product_feed.tsv exists
python generate_gmc_feed.py

# Trigger sync
curl -X POST http://localhost:5000/api/sync-merchant-api \
  -H "Content-Type: application/json" \
  -d '{"feed_path": "gmc_product_feed.tsv"}'

# Expected response:
# {
#   "success": true,
#   "products_synced": 6000,
#   "products_failed": 0,
#   "duration_seconds": 12.45,
#   "timestamp": "2026-04-06T...",
#   "merchant_id": "..."
# }
```

---

## Local Development (Without GCP)

Phase 3 includes simulated/mock functionality for local development:

### What Works Without google-cloud-merchant
- ✅ Module loads (with warnings)
- ✅ All endpoints return 503 "not enabled" (graceful)
- ✅ Code syntax is valid
- ✅ Ready for installation in production

### What Works With google-cloud-merchant Installed
- ✅ Real GCP authentication
- ✅ Actual Merchant Center sync
- ✅ Real performance metrics
- ✅ Inventory tracking

### Development Workflow
1. Local dev: Phase 3 installed but endpoints return mock data
2. Testing: Use mock endpoints to verify integration
3. Production: Full Merchant API functionality

---

## Expected API Responses (Development)

### POST /api/sync-merchant-api
```json
{
  "success": true,
  "products_synced": 6000,
  "products_failed": 0,
  "duration_seconds": 12.45,
  "timestamp": "2026-04-06T01:30:00",
  "merchant_id": "123456789"
}
```

### GET /api/merchant-insights?days=30
```json
{
  "period_days": 30,
  "timestamp": "2026-04-06T01:30:00",
  "metrics": {
    "impressions": 0,
    "clicks": 0,
    "orders": 0,
    "revenue": 0.0,
    "conversion_rate": 0.0,
    "avg_cpc": 0.0,
    "top_products": [],
    "top_categories": []
  },
  "status": "simulated"
}
```

### GET /api/phase-3-info
```json
{
  "phase_3_enabled": true,
  "merchant_api_available": false,
  "project_id": null,
  "merchant_id": null,
  "features": {
    "real_time_sync": true,
    "insights_reporting": true,
    "inventory_tracking": true
  },
  "endpoints": {
    "sync": "POST /api/sync-merchant-api",
    "insights": "GET /api/merchant-insights?days=30",
    "status": "GET /api/merchant-sync-status",
    "inventory": "GET /api/merchant-inventory"
  }
}
```

---

## Troubleshooting

### Issue: Endpoints return 503
**Solution**: Ensure `MERCHANT_API_ENABLED=True` in `.env`

### Issue: "google-cloud-merchant not installed"
**Solution**: Run `pip install google-cloud-merchant`

### Issue: Authentication error with GCP
**Solution**: 
1. Verify `GOOGLE_APPLICATION_CREDENTIALS` file exists
2. Check `GCP_PROJECT_ID` matches your project
3. Ensure Merchant API is enabled in GCP

### Issue: Feed file not found
**Solution**: Generate feed first: `python generate_gmc_feed.py`

---

## Next Steps

### For Development
1. Run: `pip install -r requirements.txt`
2. Start Flask app: `python netlify/functions/api/api.py`
3. Test endpoints with curl/Postman
4. Review `PHASE3_IMPLEMENTATION.md` for full API docs

### For Production
1. Complete GCP setup (from `PHASE1_IMPLEMENTATION.md`)
2. Set GCP credentials in production `.env`
3. Install all dependencies: `pip install -r requirements.txt`
4. Deploy to production server
5. Monitor `/api/merchant-sync-status` endpoint
6. Set up alerts for sync failures

### For Phase 4
Phase 4 will use these Phase 3 endpoints for:
- Real-time inventory checks
- AI agent session management
- Native checkout flow
- Conversion tracking

---

## Files Reference

**Phase 3 Implementation**:
- `src/merchant_api.py` - Merchant API client (500+ lines)
- `netlify/functions/api/api.py` - Flask endpoints
- `requirements.txt` - Dependencies
- `PHASE3_IMPLEMENTATION.md` - Full documentation

**Phase 3 Testing**:
- This file: `PHASE3_QUICK_START.md`

---

**Status**: Phase 3 ✅ Implementation Complete | Ready for Testing & Deployment

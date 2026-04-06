# Phase 1 Implementation Guide: UCP Infrastructure Foundation

This guide documents the Phase 1 infrastructure and security improvements made to support Universal Commerce Protocol (UCP) integration.

## What Was Done

### 1. ✅ Security: Admin Authentication with Hashed Passwords
**Problem**: Admin credentials were stored in plain text in `admin_creds.json` and compared without hashing.

**Solution Implemented**:
- Added `_ensure_admin_creds()` function that hashes admin passwords using werkzeug's `generate_password_hash()`
- Updated admin login endpoint to use `check_password_hash()` for secure comparison (no plain-text passwords in memory)
- Updated `/admin/change-credentials` endpoint to hash new passwords before storage
- Hashed passwords stored as `password_hash` field in `admin_creds.json`
- Fallback to environment variables for backwards compatibility

**Files Modified**:
- `netlify/functions/api/api.py` - Added security functions and updated auth logic

**Verification**:
```bash
# Test: Try logging in with admin credentials
# The password in admin_creds.json should now be a bcrypt hash, not plain text
cat admin_creds.json
# You should see: "password_hash": "$2b$12$..." (bcrypt hash)
```

---

### 2. ✅ Data Persistence: Initialize Required JSON Files
**Problem**: `ORDERS_FILE` and `LOYALTY_FILE` were referenced in endpoints but never defined or initialized.

**Solution Implemented**:
- Added file path definitions:
  - `DATA_DIR = data/` directory (auto-created)
  - `ORDERS_FILE = data/orders.json` (stores all customer orders)
  - `LOYALTY_FILE = data/loyalty.json` (stores loyalty points by email)
  
- Added `_ensure_data_files()` function that auto-initializes missing files on app startup
- Added `_load_json(filepath)` helper for safe JSON loading with error handling
- Added `_save_json(filepath, data)` helper for safe JSON saving
- Files are initialized with defaults: `[]` for orders, `{}` for loyalty

**Files Modified**:
- `netlify/functions/api/api.py` - Added file initialization and helper functions

**Verification**:
```bash
# Test: Start the app and check for auto-created files
ls -la data/
# You should see:
# - data/orders.json (empty list [])
# - data/loyalty.json (empty object {})

# Test: API endpoints should now work without errors
curl http://localhost:5000/api/customer/orders?email=test@example.com
# Should return 401 or valid customer data, not "file not found" errors
```

---

### 3. ✅ Credential Management: Environment Variable Template
**Problem**: No documented reference for all required environment variables and external API credentials.

**Solution Implemented**:
- Created `.env.example` file with comprehensive documentation
- Organized by section:
  - Admin authentication
  - Google APIs (Gemini, GCP, Merchant API)
  - CJ Dropshipping API
  - Payment processing (Paystack)
  - Email/SMTP (Brevo)
  - Notifications (Telegram)
  - Currency conversion
  - Merchant Center configuration
  - UCP phase-specific settings

**Usage**:
```bash
# 1. Copy template
cp .env.example .env

# 2. Fill in your actual credentials
nano .env

# 3. Set up your Python environment
export $(cat .env | xargs)

# 4. The app will load via python-dotenv automatically
```

---

## Phase 1 Checklist ✅

- [x] Admin credentials now stored with hashed passwords
- [x] Data files (orders.json, loyalty.json) auto-initialize on startup
- [x] Helper functions for safe JSON loading/saving
- [x] Environment variable template (.env.example) created
- [x] Security headers already configured in app
- [x] Backwards compatibility maintained (env vars still work)

---

## What's Not Done (Next Phases)

### Phase 2: Feed Optimization
- Extend product feed with UCP-required fields (long titles, descriptions, GTINs, high-res images, trust signals)
- Update `generate_gmc_feed.py` to include enriched data
- Update `fetch_cjdropshipping_to_csv.py` to extract additional fields from CJ API

### Phase 3: Merchant API Integration
- Implement real-time inventory sync with Google Merchant API
- Replace static TSV uploads with programmatic API calls
- Add Merchant API insights polling endpoint
- Enable features:
  - `MERCHANT_API_ENABLED=True`
  - Environment variables for GCP service account credentials

### Phase 4: Native Checkout & AI Agent Support
- Implement MCP (Model Context Protocol) server
- Integrate A2A (Agent-to-Agent) transaction framework
- Build real-time checkout integration
- Add conversion tracking with Google Data Manager
- Implement Direct Offers functionality

---

## Next Steps: GCP Service Account Setup (for Phase 3)

### Why You Need It
The Merchant API (Phase 3) requires authentication with Google Cloud. A Service Account is the recommended way to authenticate server-to-server.

### Setup Instructions

#### Step 1: Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project"
3. Name it: `ecommerce-ucp` (or your choice)
4. Wait for project creation to complete

#### Step 2: Enable Required APIs
1. In the Google Cloud Console, search for "Merchant" in the API search bar
2. Enable these APIs:
   - **Merchant API** (for product/inventory management)
   - **Identity and Access Management (IAM) API** (for service account creation)
3. Click "Enable" for each

#### Step 3: Create Service Account
1. In Google Cloud Console, go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Fill in:
   - Service account name: `ecommerce-merchant-sync`
   - Description: `Service account for UCP Merchant API integration`
4. Click **Create and Continue**

#### Step 4: Grant Permissions
1. On the "Grant roles to service account" screen, click **Add Role**
2. Search for and assign:
   - `Merchant API Admin` (full Merchant Center access)
   - `Editor` (for resource management, can be restricted later)
3. Click **Continue**

#### Step 5: Create JSON Key
1. Click **Create Key** > **JSON**
2. A file `ecommerce-merchant-sync-*.json` will download
3. **Important**: Keep this file secure! It contains authentication credentials.
4. Move it to your project directory:
   ```bash
   mv ~/Downloads/ecommerce-merchant-sync-*.json ~/Google-merchant-ecomm/gcp-service-account.json
   chmod 600 gcp-service-account.json
   ```

#### Step 6: Configure Environment
1. Update your `.env` file:
   ```
   GCP_PROJECT_ID=your-project-id-from-step-1
   GCP_SERVICE_ACCOUNT_EMAIL=ecommerce-merchant-sync@your-project.iam.gserviceaccount.com
   GOOGLE_APPLICATION_CREDENTIALS=gcp-service-account.json
   ```

2. Add to `.gitignore` (never commit the key file):
   ```
   gcp-service-account.json
   ```

#### Step 7: Verify in Google Merchant Center
1. Log into [Google Merchant Center](https://merchantcenter.google.com/)
2. Go to **Settings** > **Users and permissions**
3. You should see your service account email listed (may take a few minutes)
4. Ensure it has the appropriate Merchant Center access level

---

## Testing Phase 1 Changes

### Test 1: Admin Login with Hashed Passwords
```bash
# Run the app
python netlify/functions/api/api.py

# In another terminal, test login
curl -X POST http://localhost:5000/admin/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=change_me_in_production"

# Should redirect (302) or show login error if incorrect
```

### Test 2: Data File Initialization
```bash
# Check that files exist
ls -la data/orders.json data/loyalty.json

# Both files should exist with empty initial data
cat data/orders.json   # []
cat data/loyalty.json  # {}
```

### Test 3: Customer Orders Endpoint
```bash
# This should no longer throw "file not found" errors
curl http://localhost:5000/api/customer/orders?email=test@example.com
# Should return 401 (not logged in) or a valid JSON response
```

---

## Production Security Considerations

Before deploying Phase 1 to production:

1. **Change ADMIN_SECRET_KEY**: Use a strong random value (32+ characters)
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Secure .env file**: Never commit to git; store only in secure environment
   ```
   git add .gitignore
   echo ".env" >> .gitignore
   ```

3. **Database migration**: Consider migrating from JSON files to PostgreSQL
   - JSON is fine for MVP, but fragile for production
   - Add `DATABASE_URL` to `.env` when ready

4. **GCP Service Account Key**: Store securely, never embed in code
   - Use environment variables or secret management (Azure Key Vault, AWS Secrets Manager)
   - Rotate keys periodically

5. **Enable HTTPS**: Use SSL/TLS for all connections
   - Render.com and Netlify provide free SSL by default

6. **Audit Logging**: Add logging for all admin actions (credential changes, feed uploads, etc.)

---

## Files Modified in Phase 1

| File | Changes |
|------|---------|
| `netlify/functions/api/api.py` | Added hashed password auth, file initialization, helper functions |
| `.env.example` | Created complete environment variable reference |

## New Functions Added

```python
_ensure_admin_creds()      # Initialize admin creds with hashed password
_get_admin_creds()         # Load admin creds from file
_ensure_data_files()       # Initialize orders.json and loyalty.json
_load_json(filepath)       # Safe JSON loading with error handling
_save_json(filepath, data) # Safe JSON saving
```

---

## Summary

Phase 1 provides a **secure, initialized foundation** for UCP integration:
- ✅ Authentication system with hashed passwords (not plain text)
- ✅ Persistent data storage with auto-initialization
- ✅ Clear environment variable documentation
- ✅ Ready for Phase 2: Feed optimization
- ✅ Prepared for Phase 3: Merchant API integration (with GCP service account)

**Next**: Proceed to Phase 2 to enrich your product feed with UCP-required attributes.

# Sentinel Deployment Guide

## GCP Cloud Run Setup

### Prerequisites
- GCP Project ID: project-9801a412-f01e-45d8-9ac
- gcloud CLI installed and authenticated
- Docker installed (for local testing only)

### First-Time Deploy

Run these commands from the /sentinel/ directory:

```bash
# 1. Set your project
gcloud config set project project-9801a412-f01e-45d8-9ac

# 2. Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 3. Build and push container
gcloud builds submit --tag gcr.io/project-9801a412-f01e-45d8-9ac/marketmuse-sentinel

# 4. Deploy to Cloud Run
gcloud run deploy marketmuse-sentinel \
  --image gcr.io/project-9801a412-f01e-45d8-9ac/marketmuse-sentinel \
  --platform managed \
  --region us-east1 \
  --min-instances 1 \
  --max-instances 1 \
  --memory 256Mi \
  --cpu 1 \
  --no-allow-unauthenticated \
  --set-env-vars "RAILWAY_HEALTH_URL=https://diplomatic-mercy-production-7e61.up.railway.app/health" \
  --set-env-vars "SUPABASE_URL=https://hnfvuxcwjferoocvybnf.supabase.co" \
  --set-env-vars "TRADIER_ACCOUNT_ID=VA37545874" \
  --set-env-vars "TRADIER_SANDBOX=true" \
  --set-env-vars "HEARTBEAT_INTERVAL_SECONDS=30" \
  --set-env-vars "STALE_THRESHOLD_SECONDS=120"
```

### Secret Environment Variables (set separately via GCP Console)
These contain credentials — set via GCP Console → Cloud Run → sentinel → Edit → Variables:
- SUPABASE_SERVICE_ROLE_KEY
- TRADIER_API_KEY

### Verify Deployment
After deploy, check:
1. Cloud Run logs show "sentinel_started"
2. trading_system_health.sentinel shows status="healthy"
3. Engine Health page shows Sentinel as healthy

### Cost Estimate
Cloud Run with min-instances=1, 256Mi memory:
~$5-10/month within free trial credits.

### TRADIER_SANDBOX
Keep TRADIER_SANDBOX=true until all 12 go-live criteria pass.
In virtual mode, the Sentinel closes positions in Supabase only —
no real Tradier orders are sent.

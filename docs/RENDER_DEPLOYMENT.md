# Deploy to Render - Step by Step Guide

This guide will walk you through deploying your Omi Audio Streaming Service to Render.

## Prerequisites

1. A GitHub account
2. Your Hume AI API key (from [Hume AI Platform](https://platform.hume.ai/))
3. Your code pushed to a GitHub repository

## Step 1: Push Your Code to GitHub

If you haven't already:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Ready for Render deployment"

# Add your GitHub repo as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin master
```

## Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account (easiest option)
3. Authorize Render to access your repositories

## Step 3: Create New Web Service

1. Click **"New +"** button in the top right
2. Select **"Web Service"**
3. Connect your GitHub repository:
   - If first time: Click "Configure account" and select repositories to give access
   - Find your `audio-sentiment-profiling` repository
   - Click **"Connect"**

## Step 4: Configure Your Service

Render will auto-detect Python. Configure these settings:

### Basic Settings
- **Name**: `omi-audio-streaming` (or your preferred name)
- **Region**: Choose closest to your users
- **Branch**: `master` (or `main`)
- **Runtime**: `Python 3`

### Build & Deploy Settings
Render should auto-detect from `render.yaml`, but verify:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`

### Instance Type
- **Free** tier is fine for testing (will spin down after 15 min of inactivity)
- **Starter** ($7/month) recommended for production - stays always on

## Step 5: Add Environment Variables

Scroll down to **Environment Variables** section and add:

### Required:
- **Key**: `HUME_API_KEY`
- **Value**: Your Hume AI API key (from your `.env` file)

### Optional (for Google Cloud Storage):
- **Key**: `GCS_BUCKET_NAME`
- **Value**: Your GCS bucket name (if using GCS)

- **Key**: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
- **Value**: Your base64-encoded GCS credentials (if using GCS)

To get base64 credentials:
```bash
base64 -i path/to/your/service-account-key.json | tr -d '\n'
```

## Step 6: Deploy

1. Click **"Create Web Service"** at the bottom
2. Render will start building and deploying your app
3. Wait 2-3 minutes for the build to complete

You'll see logs showing:
```
==> Installing dependencies
==> Building application
==> Starting service
```

## Step 7: Get Your Deployment URL

Once deployed, you'll see:
- Status: **Live** (green)
- Your URL: `https://omi-audio-streaming.onrender.com` (or similar)

## Step 8: Test Your Deployment

### Test Health Endpoint
```bash
curl https://your-app-name.onrender.com/health
```

Expected response:
```json
{"status": "healthy", "service": "omi-audio-streaming"}
```

### View Dashboard
Open in browser:
```
https://your-app-name.onrender.com
```

You should see the web dashboard.

## Step 9: Configure Your Omi Device

1. Open the **Omi App** on your phone
2. Go to **Settings → Developer Mode**
3. Set **"Realtime audio bytes"** to:
   ```
   https://your-app-name.onrender.com/audio
   ```
4. Set **"Every x seconds"** to `10` (or your preferred interval)
5. Save settings

## Step 10: Monitor Your App

### View Logs
- In Render dashboard, click on your service
- Go to **"Logs"** tab
- See real-time logs of incoming requests

### View Metrics
- Go to **"Metrics"** tab
- See CPU, memory usage, and request counts

## Troubleshooting

### Build Fails
- Check **Logs** tab for error messages
- Common issues:
  - Missing dependencies in `requirements.txt`
  - Python version mismatch

### Service Not Responding
- Check if environment variables are set correctly
- Verify `HUME_API_KEY` is valid
- Check logs for startup errors

### Free Tier Spin Down
- Free tier spins down after 15 min inactivity
- First request after spin down takes ~30 seconds
- Upgrade to Starter ($7/month) for always-on service

### Audio Not Processing
- Verify your Omi device URL is correct
- Check logs for incoming requests
- Test with curl command first

## Updating Your App

When you push changes to GitHub:

```bash
git add .
git commit -m "Update feature"
git push
```

Render will **automatically rebuild and redeploy** (if auto-deploy is enabled).

## Environment Variables Management

To add/update environment variables:
1. Go to your service in Render dashboard
2. Click **"Environment"** in left sidebar
3. Add or edit variables
4. Service will automatically restart

## Custom Domain (Optional)

To use your own domain:
1. Go to **"Settings"** tab
2. Scroll to **"Custom Domain"**
3. Add your domain
4. Follow DNS configuration instructions

## Monitoring & Alerts

Set up alerts:
1. Go to **"Settings"** → **"Notifications"**
2. Add email or Slack webhook
3. Get notified of:
   - Deploy failures
   - Service crashes
   - High CPU/memory usage

## Costs

### Free Tier
- 750 hours/month free
- Spins down after 15 min inactivity
- Great for testing

### Starter Tier ($7/month)
- Always on
- Better performance
- Recommended for production

### Professional Tier ($25/month)
- More resources
- Auto-scaling
- Priority support

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
- Hume AI Docs: https://dev.hume.ai/docs

## Next Steps

1. Test your deployment thoroughly
2. Monitor logs for the first few hours
3. Set up alerts for production
4. Consider upgrading to Starter tier for always-on service
5. Add custom domain if needed

Your Omi Audio Streaming Service is now deployed and accessible worldwide!

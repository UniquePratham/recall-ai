# 🚀 Railway Deployment Guide

## Quick Deploy to Railway

### 1. Prerequisites
- GitHub account
- Railway account ([railway.app](https://railway.app))
- Your environment variables ready

### 2. Deploy Steps

#### **Option A: One-Click Deploy (Recommended)**
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

#### **Option B: Manual Deploy**

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Railway deployment ready"
   git push origin main
   ```

2. **Create Railway Project**:
   - Go to [railway.app](https://railway.app)
   - Click "Start a New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `recall-ai` repository

3. **Configure Environment Variables**:
   In Railway dashboard, add these variables:

   ```env
   BOT_TOKEN=your_actual_telegram_bot_token
   AI_PROVIDER=Gemini
   AI_MODEL=gemini-1.5-flash
   EMBEDDING_MODEL=text-embedding-004
   GEMINI_API_KEY=your_actual_gemini_api_key
   QDRANT_URL=https://your-cluster-url.qdrant.tech:6333
   QDRANT_API_KEY=your_actual_qdrant_cloud_api_key
   QDRANT_COLLECTION_NAME=recall_documents
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/recall_ai
   SECRET_KEY=your_secret_key_here
   LOG_LEVEL=INFO
   ```

4. **Deploy**:
   - Railway will automatically build and deploy using the Dockerfile
   - Monitor deployment in Railway dashboard
   - Check health at: `https://your-app.railway.app/health`

### 3. External Services Setup

#### **Qdrant Cloud (Vector Database)**
1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create free 1GB cluster
3. Copy cluster URL and API key
4. Add to Railway environment variables

#### **MongoDB Atlas (Document Database)**
1. Sign up at [mongodb.com/atlas](https://mongodb.com/atlas)
2. Create free 512MB cluster
3. Create database user
4. Get connection string
5. Add to Railway environment variables

#### **Google Gemini API**
1. Go to [ai.google.dev](https://ai.google.dev)
2. Create API key
3. Add to Railway environment variables

### 4. Monitoring

#### **Health Check**
- URL: `https://your-app.railway.app/health`
- Returns: `{"status": "healthy", "timestamp": 1234567890}`

#### **Railway Dashboard**
- Real-time logs
- Resource usage
- Deployment status
- Environment variables

#### **Cost Monitoring**
- Railway: $5/month free credit
- Qdrant: Free 1GB tier
- MongoDB: Free 512MB tier
- Gemini API: Pay per use (~$0.50/month)

### 5. Custom Domain (Optional)

1. In Railway dashboard, go to "Settings" → "Domains"
2. Add your custom domain
3. Update DNS records as shown
4. Enable SSL (automatic)

### 6. Troubleshooting

#### **Common Issues**:

1. **Bot not responding**:
   - Check Railway logs for errors
   - Verify BOT_TOKEN is correct
   - Ensure health check is passing

2. **Database connection failed**:
   - Verify MONGODB_URI format
   - Check MongoDB Atlas IP whitelist (allow all: 0.0.0.0/0)
   - Ensure database user has read/write permissions

3. **AI provider errors**:
   - Verify API key for selected provider
   - Check API quotas/limits
   - Ensure AI_PROVIDER matches your API key

4. **Vector database issues**:
   - Verify Qdrant Cloud URL and API key
   - Check Qdrant cluster status
   - Ensure collection name is correct

#### **Logs Access**:
```bash
# View Railway logs (if using CLI)
railway logs
```

### 7. Updates

To update your deployed bot:
```bash
git add .
git commit -m "Update bot features"
git push origin main
```

Railway will automatically redeploy with the latest changes.

### 8. Scaling

- **Free tier**: Sufficient for personal use (1000+ messages/day)
- **Pro tier**: $20/month for unlimited usage
- **Auto-scaling**: Railway handles traffic spikes automatically

## 🎉 Success!

Your Recall AI bot is now running 24/7 in the cloud!

- **Access**: Chat with your Telegram bot
- **Monitor**: Check Railway dashboard
- **Health**: Visit your app's `/health` endpoint
- **Logs**: View real-time logs in Railway
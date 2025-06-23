# Deployment Guide

This guide covers multiple deployment options for the LLM Screening Tool.

## Prerequisites

Before deploying, ensure you have:
- OpenAI API key (`OPENAI_API_KEY`)
- Anthropic API key (`ANTHROPIC_API_KEY`)
- Email address for PubMed access (`ENTREZ_EMAIL`)

## Quick Deploy Options

### 1. Railway (Recommended)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template)

**Steps:**
1. Click the Railway button above or go to [Railway](https://railway.app)
2. Connect your GitHub repository
3. Set environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `ENTREZ_EMAIL`: Your email for PubMed API
4. Deploy automatically uses `railway.json` configuration

**Cost:** ~$5/month with Railway's hobby plan

### 2. Heroku

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

**Steps:**
1. Click the Heroku button above
2. Fill in the required environment variables
3. Deploy using the `app.json` configuration

**Cost:** ~$7/month with Heroku's basic plan

### 3. Render

**Steps:**
1. Fork this repository
2. Go to [Render](https://render.com)
3. Create new "Web Service"
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml`
6. Set environment variables in Render dashboard

**Cost:** Free tier available, ~$7/month for paid

### 4. DigitalOcean App Platform

**Steps:**
1. Go to [DigitalOcean Apps](https://cloud.digitalocean.com/apps)
2. Create new app from GitHub repository
3. DigitalOcean will detect Python application
4. Set environment variables
5. Deploy

**Cost:** ~$12/month with basic plan

## Docker Deployment

### Local Docker

```bash
# Build the image
docker build -t llm-screening-tool .

# Run with environment variables
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=your-key \
  -e ANTHROPIC_API_KEY=your-key \
  -e ENTREZ_EMAIL=your-email \
  -e SECRET_KEY=your-secret \
  llm-screening-tool
```

### Docker Compose

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env

# Start with Docker Compose
docker-compose up -d
```

## Manual VPS Deployment

### Requirements
- Ubuntu 20.04+ or similar
- Python 3.11+
- Nginx (optional, for reverse proxy)

### Steps

1. **Clone and setup:**
```bash
git clone https://github.com/your-username/llm-screening-tool.git
cd llm-screening-tool
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Environment setup:**
```bash
cp .env.example .env
nano .env  # Add your API keys
```

3. **Run application:**
```bash
python run.py
```

4. **Production setup with Gunicorn:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

5. **Nginx reverse proxy (optional):**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_ENV` | No | Set to 'production' for deployment |
| `SECRET_KEY` | Yes | Flask secret key (auto-generated on most platforms) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude models |
| `ENTREZ_EMAIL` | Yes | Email for PubMed API access |
| `PORT` | No | Port to run on (default: 5000) |
| `DATABASE_URL` | No | Database URL (default: SQLite) |

## SSL/HTTPS

Most cloud platforms (Railway, Heroku, Render) provide automatic HTTPS certificates. For manual deployments, consider:

- **Let's Encrypt with Certbot**
- **Cloudflare** (free SSL proxy)
- **AWS Certificate Manager** (if using AWS)

## Monitoring & Logs

### Cloud Platform Logs
- **Railway:** Built-in logs dashboard
- **Heroku:** `heroku logs --tail`
- **Render:** Logs in dashboard
- **DigitalOcean:** Logs in app dashboard

### Custom Monitoring
Consider adding:
- **Sentry** for error tracking
- **New Relic** or **DataDog** for performance monitoring
- **Uptime Robot** for availability monitoring

## Scaling Considerations

For high-volume usage:

1. **Database:** Switch from SQLite to PostgreSQL
2. **Caching:** Add Redis for session/result caching
3. **Load Balancing:** Use multiple application instances
4. **File Storage:** Use cloud storage (AWS S3, etc.)
5. **CDN:** Use CloudFront or similar for static assets

## Security Notes

- Never commit API keys to version control
- Use environment variables for all secrets
- Keep dependencies updated: `pip list --outdated`
- Monitor API usage to prevent unexpected costs
- Set up rate limiting for production use

## Troubleshooting

### Common Issues

1. **Port binding errors:** Ensure PORT environment variable is set correctly
2. **API key errors:** Verify all required environment variables are set
3. **Database errors:** Check if database initialization completed
4. **Memory issues:** Consider upgrading to higher-tier plans for large files

### Getting Help

- Check logs first using platform-specific tools
- Verify all environment variables are set
- Test locally with same configuration
- Check API key permissions and quotas

## Cost Estimation

| Platform | Monthly Cost | Features |
|----------|-------------|----------|
| Railway | $5+ | Auto-deploy, metrics |
| Heroku | $7+ | Add-ons, pipelines |
| Render | Free/$7+ | Auto-deploy, free tier |
| DigitalOcean | $12+ | More control, SSH access |
| VPS (manual) | $5+ | Full control, more setup |

*Costs exclude API usage fees from OpenAI/Anthropic*
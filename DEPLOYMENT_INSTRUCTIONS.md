# Nova Voice - Deployment Instructions

## ✅ Completed Setup

1. **Cloudflare Tunnel** - Running with auto-start on Windows boot
2. **DNS Configuration** - All subdomains configured:
   - `ws.nova-voice.com` → WebSocket (port 5026)
   - `api.nova-voice.com` → API/Health (port 8080)
   - `auth.nova-voice.com` → Auth (port 8080)
3. **Environment Files** - `.env` files configured in `gateway/` and `infra/`
4. **Cloud Storage** - Nova UI .exe uploaded to: `https://downloads.nova-voice.com/Nova%20UI%20Setup%200.1.0.exe`

## 📝 Changes Made

### Nova-UI (electron/main.js)
Updated production URLs to match your Cloudflare Tunnel setup:
- **WebSocket URL**: `wss://ws.nova-voice.com` (was `wss://nova-voice.com:5026`)
- **Backend URL**: `https://api.nova-voice.com` (was `https://nova-voice.com:8080`)
- **OAuth Redirect**: `https://auth.nova-voice.com/auth/callback` (was `https://nova-voice.com:8080/auth/callback`)

**Why:** Cloudflare Tunnel handles SSL/TLS on standard port 443, so we removed port numbers and use proper subdomains.

### Nova-Web (src/components/DownloadCTA.tsx)
Added download functionality to the button:
- **Line 52**: Added `onClick` handler that downloads the .exe from your cloud storage
- **Download URL**: `https://downloads.nova-voice.com/Nova%20UI%20Setup%200.1.0.exe`

**Why:** When users click "Download Nova Voice", it will now trigger the actual .exe download.

## 🚀 Next Steps

### 1. Update OAuth Redirect URIs (Critical!)

You need to update the redirect URIs in ALL your OAuth provider consoles to match the new URL:

**New Redirect URI for ALL providers:** `https://auth.nova-voice.com/auth/callback`

#### Google Cloud Console
1. Go to: https://console.cloud.google.com/apis/credentials
2. Select your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", add: `https://auth.nova-voice.com/auth/callback`
4. Save

#### GitHub OAuth App
1. Go to: https://github.com/settings/developers
2. Select your OAuth App
3. Update "Authorization callback URL" to: `https://auth.nova-voice.com/auth/callback`
4. Save

#### Microsoft Azure
1. Go to: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
2. Select your app registration
3. Go to "Authentication" → "Platform configurations" → "Web"
4. Add redirect URI: `https://auth.nova-voice.com/auth/callback`
5. Save

#### Discord Developer Portal
1. Go to: https://discord.com/developers/applications
2. Select your application
3. Go to "OAuth2" → "Redirects"
4. Add: `https://auth.nova-voice.com/auth/callback`
5. Save

### 2. Rebuild Nova-UI Application

Since we updated the production URLs, you need to rebuild the Electron app:

```powershell
cd Nova-UI
npm run build
npm run electron-build
```

**Output:** New `.exe` file will be created in `Nova-UI/dist/Nova UI Setup 0.1.0.exe`

**Important:** Upload this NEW .exe to your cloud storage (replace the old one) because it contains the updated production URLs.

### 3. Start Docker Services

Start all backend services:

```powershell
cd infra
docker-compose up -d
```

Verify services are running:
```powershell
# Check service status
docker-compose ps

# Check logs
docker-compose logs -f gateway
docker-compose logs -f stt_worker
docker-compose logs -f translation_worker

# Test health endpoints locally
curl http://localhost:8080/health
```

Test via Cloudflare Tunnel:
```powershell
# Test API health endpoint (should return JSON)
curl https://api.nova-voice.com/health
```

### 4. Deploy Nova-Web to Cloudflare Pages

**Manual Deploy:**
```powershell
cd Nova-Web
npm install
npm run build
npx wrangler pages deploy dist --project-name=nova-voice-web
```

**Or via Cloudflare Dashboard:**
1. Go to Cloudflare Dashboard → Pages
2. Create new project or update existing
3. Connect to GitHub repository
4. Build settings:
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `Nova-Web` (if repo has multiple folders)
5. Add custom domain: `nova-voice.com`
6. Deploy

### 5. Test Complete Flow

1. **Visit landing page:** https://nova-voice.com
2. **Click "Download Nova Voice"** - Should download the .exe file
3. **Install the application**
4. **Launch Nova Voice**
5. **Click "Login"** - Test OAuth authentication (should redirect to `auth.nova-voice.com`)
6. **Test voice typing mode** - Verify WebSocket connects to `ws.nova-voice.com`
7. **Test live subtitle mode** - Verify transcription works
8. **Check translation** - If enabled, verify translations appear

### 6. Monitor Services

**View logs:**
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f gateway
```

**Check Cloudflare Tunnel status:**
```powershell
cloudflared tunnel info Nova-Voice
```

**Restart services if needed:**
```powershell
docker-compose restart gateway
docker-compose restart stt_worker
docker-compose restart translation_worker
```

## 🔒 Security Checklist

- [ ] OAuth redirect URIs updated in all provider consoles
- [ ] JWT_SECRET is strong and secure (at least 32 characters)
- [ ] `.env` files are NOT committed to git (check `.gitignore`)
- [ ] Cloudflare SSL/TLS mode set to "Full" or "Full (strict)"
- [ ] Cloudflare Web Application Firewall (WAF) enabled
- [ ] Rate limiting configured in Cloudflare
- [ ] DDoS protection enabled (automatic with Cloudflare)

## 🐛 Troubleshooting

### WebSocket Connection Fails
- Check Cloudflare Tunnel is running: `cloudflared service status`
- Verify DNS: `nslookup ws.nova-voice.com` should resolve
- Check gateway logs: `docker-compose logs gateway`
- Test locally first: `ws://localhost:5026`

### OAuth Authentication Fails
- Verify redirect URI is EXACTLY: `https://auth.nova-voice.com/auth/callback`
- Check OAuth credentials in `gateway/.env`
- Look for errors in gateway logs
- Ensure all OAuth apps are enabled in provider consoles

### Download Button Doesn't Work
- Check browser console for errors (F12)
- Verify cloud storage URL is accessible: Visit `https://downloads.nova-voice.com/Nova%20UI%20Setup%200.1.0.exe`
- Check if URL encoding is correct (%20 for spaces)

### Services Won't Start
- Check Docker is running
- Verify all environment variables in `infra/.env` and `gateway/.env`
- Check for port conflicts: `netstat -ano | findstr :5026` and `netstat -ano | findstr :8080`
- Review Docker logs for specific errors

### GPU Not Detected (if using NVIDIA GPU)
- Ensure `runtime: nvidia` is in docker-compose.yml
- Install NVIDIA Container Toolkit
- Verify GPU is accessible: `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`

## 📊 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Landing Page | https://nova-voice.com | Public website |
| WebSocket | wss://ws.nova-voice.com | Real-time audio streaming |
| API/Health | https://api.nova-voice.com/health | Health checks & API |
| Auth | https://auth.nova-voice.com/auth/callback | OAuth callbacks |
| Download | https://downloads.nova-voice.com/Nova%20UI%20Setup%200.1.0.exe | App download |

## 🎉 Launch Checklist

- [ ] Docker services running (gateway, stt_worker, translation_worker, redis)
- [ ] Cloudflare Tunnel active and auto-starting
- [ ] Nova-UI rebuilt with new production URLs
- [ ] New .exe uploaded to cloud storage
- [ ] OAuth redirect URIs updated in all providers
- [ ] Nova-Web deployed to Cloudflare Pages
- [ ] Landing page accessible at nova-voice.com
- [ ] Download button works and downloads correct .exe
- [ ] Application installs and launches successfully
- [ ] OAuth login works
- [ ] Voice typing mode connects and transcribes
- [ ] Live subtitle mode works
- [ ] Translation functionality operational

## 📞 Support

If you encounter issues:
1. Check service logs: `docker-compose logs -f`
2. Verify Cloudflare Tunnel: `cloudflared tunnel info Nova-Voice`
3. Test health endpoint: `curl https://api.nova-voice.com/health`
4. Check DNS resolution: `nslookup ws.nova-voice.com`
5. Review browser console (F12) for frontend errors

---

**Last Updated:** After completing Nova-UI URL updates and Nova-Web download button integration


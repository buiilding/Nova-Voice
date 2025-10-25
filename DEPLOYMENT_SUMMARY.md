# Nova Voice Platform - Deployment Summary

## ✅ Completed Tasks

### 1. Environment Configuration
- ✅ `infra/.env` - Already configured
- ✅ `gateway/.env` - Already configured with JWT_SECRET and OAuth credentials

### 2. Cloudflare Tunnel Setup
- ✅ Tunnel "Nova-Voice" created and running
- ✅ Auto-starts on Windows boot via Task Scheduler
- ✅ DNS routing configured:
  - `ws.nova-voice.com` → localhost:5026 (WebSocket)
  - `api.nova-voice.com` → localhost:8080 (API/Health)
  - `auth.nova-voice.com` → localhost:8080 (Auth)

### 3. Nova-UI Updates
- ✅ Updated WebSocket URL: `wss://ws.nova-voice.com` (was `wss://nova-voice.com:5026`)
- ✅ Updated Backend URL: `https://api.nova-voice.com` (was `https://nova-voice.com:8080`)
- ✅ Updated OAuth Redirect: `https://auth.nova-voice.com/auth/callback`
- ✅ File modified: `Nova-UI/electron/main.js` (lines 52-77)

### 4. Cloud Storage
- ✅ .exe uploaded to Cloudflare R2
- ✅ Download URL: `https://downloads.nova-voice.com/Nova%20UI%20Setup%200.1.0.exe`

### 5. Nova-Web Updates
- ✅ Download button updated with onClick handler
- ✅ Downloads .exe from cloud storage
- ✅ File modified: `Nova-Web/src/components/DownloadCTA.tsx` (line 52)

---

## 🔄 Next Steps (In Order)

### Step 1: Rebuild Nova-UI Application ⚠️ CRITICAL
**Why:** The production URLs have been updated, so you need to rebuild the .exe with the new configuration.

```powershell
cd Nova-UI
npm install
npm run build
npm run electron-build
```

**Output:** New `.exe` will be in `Nova-UI/dist/Nova UI Setup 0.1.0.exe`

**Important:** After building, upload this NEW .exe to replace the old one in cloud storage.

---

### Step 2: Update OAuth Redirect URIs ⚠️ CRITICAL

**New Redirect URI for ALL providers:**
```
https://auth.nova-voice.com/auth/callback
```

#### Google Cloud Console
1. Go to: https://console.cloud.google.com/apis/credentials
2. Select your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", add: `https://auth.nova-voice.com/auth/callback`
4. Save

#### GitHub
1. Go to: https://github.com/settings/developers
2. Select your OAuth App
3. Update "Authorization callback URL" to: `https://auth.nova-voice.com/auth/callback`
4. Save

#### Microsoft Azure
1. Go to: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
2. Select your app → "Authentication" → "Web"
3. Add redirect URI: `https://auth.nova-voice.com/auth/callback`
4. Save

#### Discord
1. Go to: https://discord.com/developers/applications
2. Select your app → "OAuth2" → "Redirects"
3. Add: `https://auth.nova-voice.com/auth/callback`
4. Save

**See `OAUTH_SETUP_GUIDE.md` for detailed instructions.**

---

### Step 3: Start Backend Services

```powershell
cd infra
docker-compose up -d
```

**Verify services are running:**
```powershell
# Check status
docker-compose ps

# Check logs
docker-compose logs -f gateway
docker-compose logs -f stt_worker
docker-compose logs -f translation_worker

# Test health endpoint locally
curl http://localhost:8080/health

# Test via Cloudflare Tunnel
curl https://api.nova-voice.com/health
```

---

### Step 4: Deploy Nova-Web to Cloudflare Pages

**Manual Deploy (Recommended):**
```powershell
cd Nova-Web
npm install
npm run build
npx wrangler pages deploy dist --project-name=nova-voice-web
```

**Or via Cloudflare Dashboard:**
1. Go to Cloudflare Dashboard → Pages
2. Create project or update existing
3. Connect to GitHub repository
4. Build settings:
   - Build command: `npm run build`
   - Build output directory: `dist`
5. Add custom domain: `nova-voice.com`
6. Deploy

---

### Step 5: End-to-End Testing

1. **Visit Landing Page:** https://nova-voice.com
2. **Click "Download Nova Voice"** → Should download .exe from `https://downloads.nova-voice.com/Nova%20UI%20Setup%200.1.0.exe`
3. **Install Application**
4. **Launch Nova Voice**
5. **Test Authentication:**
   - Click "Login"
   - Try each OAuth provider (Google, GitHub, Microsoft, Discord)
   - Verify successful login
6. **Test Voice Typing Mode:**
   - Enable voice typing mode (Ctrl+V)
   - Speak into microphone
   - Verify text appears in target application
7. **Test Live Subtitle Mode:**
   - Enable live subtitle mode (Ctrl+L)
   - Speak into microphone
   - Verify subtitles appear in overlay
8. **Test Translation:**
   - Enable translation
   - Select source and target languages
   - Verify translation works

---

## 📋 Quick Commands Reference

### Docker Management
```powershell
# Start services
cd infra && docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart gateway

# Check service status
docker-compose ps
```

### Build Commands
```powershell
# Build Nova-UI
cd Nova-UI
npm run build && npm run electron-build

# Build Nova-Web
cd Nova-Web
npm run build
```

### Cloudflare Tunnel
```powershell
# Check tunnel status
cloudflared tunnel info Nova-Voice

# View tunnel logs
cloudflared tunnel run Nova-Voice

# Restart tunnel (if needed)
sc stop cloudflared
sc start cloudflared
```

---

## 🔧 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     nova-voice.com                           │
│                  (Cloudflare Pages)                          │
│                   Nova-Web Landing                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Download Button
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              downloads.nova-voice.com                        │
│                  (Cloudflare R2)                             │
│              Nova UI Setup 0.1.0.exe                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ User Installs
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Nova UI Desktop App                       │
│                   (Electron Application)                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket & Auth
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Cloudflare Tunnel                           │
│                    (On Your PC)                              │
│                                                              │
│  ws.nova-voice.com    → localhost:5026 (WebSocket)          │
│  api.nova-voice.com   → localhost:8080 (API/Health)         │
│  auth.nova-voice.com  → localhost:8080 (OAuth)              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                Docker Services (Local PC)                    │
│                                                              │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐           │
│  │ Gateway  │  │ STT Worker │  │ Translation  │           │
│  │ :5026    │  │            │  │   Worker     │           │
│  │ :8080    │  │            │  │              │           │
│  └──────────┘  └────────────┘  └──────────────┘           │
│       │              │                  │                   │
│       └──────────────┴──────────────────┘                   │
│                      │                                       │
│              ┌───────────────┐                              │
│              │  Redis :6379  │                              │
│              └───────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Modified Files Summary

| File | Changes | Status |
|------|---------|--------|
| `Nova-UI/electron/main.js` | Updated production URLs (lines 52-77) | ✅ Completed |
| `Nova-Web/src/components/DownloadCTA.tsx` | Added download onClick handler (line 52) | ✅ Completed |
| `infra/.env` | Environment variables | ✅ Already exists |
| `gateway/.env` | JWT & OAuth credentials | ✅ Already exists |

---

## 🔒 Security Checklist

- ✅ JWT_SECRET configured in gateway/.env
- ✅ OAuth credentials configured
- ✅ Cloudflare SSL enabled (automatic)
- ✅ .env files in .gitignore
- ⏳ OAuth redirect URIs updated (PENDING - Step 2)
- ⏳ WAF enabled in Cloudflare (RECOMMENDED)
- ⏳ Rate limiting configured (RECOMMENDED)

---

## 📚 Documentation Files Created

1. **`DEPLOYMENT_INSTRUCTIONS.md`** - Comprehensive deployment guide with step-by-step instructions
2. **`OAUTH_SETUP_GUIDE.md`** - Detailed OAuth setup for all providers (Google, GitHub, Microsoft, Discord)
3. **`DEPLOYMENT_SUMMARY.md`** (this file) - Quick reference and status overview

---

## ⚠️ Important Notes

1. **Rebuild Required:** You MUST rebuild Nova-UI after the URL changes and re-upload the .exe
2. **OAuth Critical:** Update ALL OAuth redirect URIs or authentication will fail
3. **Testing First:** Test locally before deploying to production
4. **Backup:** Keep the old .exe until you verify the new one works

---

## 🆘 Troubleshooting

### WebSocket Won't Connect
- Check: `docker-compose ps` - Gateway running?
- Check: `cloudflared tunnel info Nova-Voice` - Tunnel running?
- Test: `curl https://api.nova-voice.com/health`

### OAuth Fails
- Verify redirect URI is EXACTLY: `https://auth.nova-voice.com/auth/callback`
- Check gateway logs: `docker-compose logs gateway`
- Verify credentials in `gateway/.env`

### Download Button Not Working
- Check browser console (F12) for errors
- Verify URL is accessible: Visit download link directly
- Check cloud storage permissions

---

## 🎯 Current Status

**Ready for:** Step 1 (Rebuild Nova-UI)

**After rebuilding, proceed with:** Steps 2-5 in order

**Estimated Time to Complete:** 30-60 minutes (depending on build time and OAuth setup)

---

Last Updated: After Nova-UI and Nova-Web code changes


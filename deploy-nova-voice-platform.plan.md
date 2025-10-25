<!-- a78e044e-cb7a-4ce7-b92a-5a5c662e735f 85cc1d22-6c09-446a-ae5e-3d3fd9227697 -->
# Deploy Nova Voice Platform

## Overview

Configure Nova-UI Electron app to connect to your local backend through nova-voice.com, build the .exe installer, deploy Nova-Web landing page to Cloudflare Pages, and enable users worldwide to download and use the app.

## Changes Required

### 1. Update Nova-UI Backend Connection URLs

**File: `Nova-UI/electron/main.js` (lines 52-77)**

Currently uses `wss://nova-voice.com:5026` and `https://nova-voice.com:8080` in production mode, which is correct. However, need to ensure all production URLs are consistent:

- WebSocket Gateway: `wss://nova-voice.com:5026`
- Backend API: `https://nova-voice.com:8080`
- Discovery Service: `https://nova-voice.com:5025`
- OAuth Redirect: `https://auth.nova-voice.com/auth/callback`

**File: `Nova-UI/app/page.tsx` (line 49)**

Change:

```typescript
const backendUrl = process.env.NODE_ENV === 'production'
  ? 'https://nova-voice.com:8080'
  : 'http://localhost:8080';
```

### 2. Create Production Environment File

**New file: `Nova-UI/.env.production`**

```env
NODE_ENV=production
BACKEND_URL=https://nova-voice.com:8080
GATEWAY_URL=wss://nova-voice.com:5026
DISCOVERY_URL=https://nova-voice.com:5025
```

### 3. Build Nova-UI Electron App

Build the Windows .exe installer:

```bash
cd Nova-UI
npm install
npm run build
npm run dist
```

This creates `Nova-UI/dist/Nova UI Setup 0.1.0.exe`

### 4. Update Nova-Web Download Button

**File: `Nova-Web/src/components/DownloadCTA.tsx` (line 49-58)**

Add download link to the Button component:

```tsx
<Button 
  size="lg" 
  className="group relative px-12 py-6 bg-primary hover:bg-primary/80 text-primary-foreground transition-all duration-300 shadow-2xl hover:shadow-primary/50 text-lg"
  asChild
>
  <a href="/downloads/Nova-UI-Setup.exe" download>
    <Download className="w-6 h-6 mr-3" />
    Download Nova Voice
    <div className="absolute inset-0 bg-primary/40 rounded-lg blur-xl group-hover:blur-2xl transition-all duration-300 -z-10" />
  </a>
</Button>
```

### 5. Prepare Nova-Web for Deployment

**Create `Nova-Web/public/downloads/` directory and copy .exe file**

After building Nova-UI, copy the .exe to Nova-Web public folder:

```bash
mkdir Nova-Web/public/downloads
cp "Nova-UI/dist/Nova UI Setup 0.1.0.exe" Nova-Web/public/downloads/Nova-UI-Setup.exe
```

**Build Nova-Web:**

```bash
cd Nova-Web
npm install
npm run build
```

This creates the `Nova-Web/build/` directory with the static site.

### 6. Deploy to Cloudflare Pages

**Option A: Using Wrangler CLI (Recommended)**

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Deploy from Nova-Web/build directory
cd Nova-Web
wrangler pages deploy build --project-name=nova-voice
```

**Option B: Using Cloudflare Dashboard**

1. Go to Cloudflare Dashboard → Pages
2. Create new project → Connect to Git OR Upload assets
3. If uploading: Drag the `Nova-Web/build` folder
4. Project name: `nova-voice`
5. Custom domain: `nova-voice.com` (or `www.nova-voice.com`)

### 7. Configure Cloudflare DNS

If not already configured, add/update DNS records:

- **A/CNAME record for `nova-voice.com`**: Points to Cloudflare Pages
- **CNAME records via tunnel** (already done per DEPLOYMENT_README):
    - Uses ports directly on domain (nova-voice.com:5026, nova-voice.com:8080)

### 8. Update Cloudflare Tunnel Configuration

**File: `~/.cloudflared/config.yaml`**

Ensure the tunnel configuration exposes the correct ports:

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /path/to/credentials.json

ingress:
  # WebSocket endpoint (port 5026)
 - hostname: nova-voice.com
    path: ^/ws
    service: http://localhost:5026
    originRequest:
      noTLSVerify: true
      
  # Backend API (port 8080)
 - hostname: nova-voice.com
    service: http://localhost:8080
    originRequest:
      noTLSVerify: true
      
  # Catch-all
 - service: http_status:404
```

Or if using port-based access directly (nova-voice.com:5026):

- Ensure Cloudflare Tunnel forwards ports 5026, 8080, 5025
- Cloudflare may need port forwarding configured in Application settings

### 9. Test Complete Flow

1. **Test backend connectivity:**
   ```bash
   curl https://nova-voice.com:8080/health
   ```

2. **Test WebSocket:** Use browser console or wscat
   ```bash
   wscat -c wss://nova-voice.com:5026
   ```

3. **Test website:** Visit `https://nova-voice.com`

4. **Test download:** Click download button, install .exe, and test connection

## Key Files Changed

- `Nova-UI/electron/main.js` (verify production URLs)
- `Nova-UI/app/page.tsx` (update backend URL)
- `Nova-Web/src/components/DownloadCTA.tsx` (add download link)
- `Nova-Web/public/downloads/Nova-UI-Setup.exe` (add .exe file)
- `~/.cloudflared/config.yaml` (verify tunnel config)

## Post-Deployment

1. **Update .exe when needed:**

      - Rebuild Nova-UI: `npm run dist`
      - Copy new .exe to `Nova-Web/public/downloads/`
      - Redeploy Nova-Web: `wrangler pages deploy build`

2. **Monitor backend:**

      - Keep Docker services running: `docker-compose up -d`
      - Check Cloudflare Tunnel: `cloudflared tunnel list`
      - Monitor logs: `docker-compose logs -f gateway`

3. **SSL/TLS Note:**

      - Cloudflare provides free SSL for nova-voice.com
      - Ensure Cloudflare SSL mode is "Full" or "Flexible"
      - Ports 5026, 8080 need to be accessible through Cloudflare

### To-dos

- [ ] Verify and update production URLs in Nova-UI Electron app
- [ ] Build Nova-UI Electron app to generate .exe installer
- [ ] Update Nova-Web download button with .exe link
- [ ] Copy .exe file to Nova-Web public/downloads directory
- [ ] Build Nova-Web for production deployment
- [ ] Deploy Nova-Web to Cloudflare Pages with custom domain
- [ ] Verify Cloudflare Tunnel configuration for port access
- [ ] Test complete flow: website, download, app connection
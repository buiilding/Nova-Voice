# Nova Voice - Quick Start Guide

## 🚀 What's Been Done

✅ Nova-UI production URLs updated  
✅ Nova-Web download button configured  
✅ Cloudflare Tunnel running  
✅ DNS configured  
✅ .env files configured  

## ⚡ What You Need to Do (30 mins)

### 1. Rebuild Nova-UI (5 mins)
```powershell
cd Nova-UI
npm install
npm run build
npm run electron-build
```
📤 Upload the new .exe from `Nova-UI/dist/` to cloud storage (replace old one)

### 2. Update OAuth Redirects (10 mins)
Update redirect URI to `https://auth.nova-voice.com/auth/callback` in:
- [Google Console](https://console.cloud.google.com/apis/credentials)
- [GitHub Settings](https://github.com/settings/developers)
- [Azure Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
- [Discord Dev Portal](https://discord.com/developers/applications)

See `OAUTH_SETUP_GUIDE.md` for details.

### 3. Start Backend (2 mins)
```powershell
cd infra
docker-compose up -d
```

Verify: `curl https://api.nova-voice.com/health`

### 4. Deploy Nova-Web (3 mins)
```powershell
cd Nova-Web
npm install
npm run build
npx wrangler pages deploy dist --project-name=nova-voice-web
```

### 5. Test Everything (10 mins)
1. Visit https://nova-voice.com
2. Click "Download Nova Voice"
3. Install and launch app
4. Test login with OAuth
5. Test voice typing (Ctrl+V)
6. Test live subtitles (Ctrl+L)

## 📖 Full Documentation

- **`DEPLOYMENT_SUMMARY.md`** - Complete status and next steps
- **`DEPLOYMENT_INSTRUCTIONS.md`** - Detailed deployment guide
- **`OAUTH_SETUP_GUIDE.md`** - OAuth provider setup
- **`deploy-nova-voice-platform.plan.md`** - Original deployment plan

## 🆘 Need Help?

Check Docker logs: `docker-compose logs -f`  
Check tunnel: `cloudflared tunnel info Nova-Voice`  
Test API: `curl https://api.nova-voice.com/health`

---

**Ready to start? Begin with Step 1! 🎯**


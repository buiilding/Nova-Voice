# OAuth Provider Setup Guide

## Quick Reference

**New OAuth Redirect URI (for ALL providers):**
```
https://auth.nova-voice.com/auth/callback
```

## Detailed Setup Instructions

### 1. Google OAuth Setup

#### Create/Update OAuth Client

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/apis/credentials
   - Select your project (or create a new one)

2. **Enable Required APIs:**
   - Go to "Library" → Search for "Google+ API"
   - Click "Enable"

3. **Create OAuth 2.0 Client ID:**
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Web application"
   - Name: "Nova Voice Desktop App"

4. **Configure OAuth Consent Screen:**
   - User Type: External (for public users) or Internal (for organization only)
   - App name: "Nova Voice"
   - User support email: your-email@example.com
   - Developer contact: your-email@example.com
   - Scopes: Add "email" and "profile"

5. **Add Authorized Redirect URIs:**
   ```
   https://auth.nova-voice.com/auth/callback
   http://localhost:8080/auth/callback  (for development)
   ```

6. **Get Credentials:**
   - Copy "Client ID" → Add to `gateway/.env` as `GOOGLE_CLIENT_ID`
   - Copy "Client Secret" → Add to `gateway/.env` as `GOOGLE_CLIENT_SECRET`

---

### 2. GitHub OAuth Setup

#### Create OAuth App

1. **Go to GitHub Developer Settings:**
   - Visit: https://github.com/settings/developers
   - Click "New OAuth App"

2. **Fill in Application Details:**
   - Application name: `Nova Voice`
   - Homepage URL: `https://nova-voice.com`
   - Authorization callback URL: `https://auth.nova-voice.com/auth/callback`
   - Application description: "AI-powered voice typing and translation"

3. **Register Application**

4. **Get Credentials:**
   - Copy "Client ID" → Add to `gateway/.env` as `GITHUB_CLIENT_ID`
   - Click "Generate a new client secret"
   - Copy "Client Secret" → Add to `gateway/.env` as `GITHUB_CLIENT_SECRET`

5. **Optional - Add Development Callback:**
   - You can add multiple callback URLs if needed
   - Add: `http://localhost:8080/auth/callback` for local testing

---

### 3. Microsoft/Azure OAuth Setup

#### Create App Registration

1. **Go to Azure Portal:**
   - Visit: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
   - Click "New registration"

2. **Register Application:**
   - Name: `Nova Voice`
   - Supported account types: 
     - "Accounts in any organizational directory and personal Microsoft accounts" (most common)
   - Redirect URI:
     - Platform: Web
     - URI: `https://auth.nova-voice.com/auth/callback`
   - Click "Register"

3. **Add Additional Redirect URIs (optional):**
   - Go to "Authentication" → "Platform configurations" → "Web"
   - Add: `http://localhost:8080/auth/callback` (for development)
   - Save

4. **Configure Token Settings:**
   - Still in "Authentication"
   - Check "Access tokens" and "ID tokens" under "Implicit grant and hybrid flows"
   - Save

5. **Get Application ID:**
   - Go to "Overview"
   - Copy "Application (client) ID" → Add to `gateway/.env` as `MICROSOFT_CLIENT_ID`
   - Copy "Directory (tenant) ID" → Add to `gateway/.env` as `MICROSOFT_TENANT_ID` (optional, defaults to 'common')

6. **Create Client Secret:**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Description: "Nova Voice Backend"
   - Expires: Choose duration (24 months recommended)
   - Click "Add"
   - Copy the **Value** (not Secret ID) → Add to `gateway/.env` as `MICROSOFT_CLIENT_SECRET`
   - ⚠️ **Important:** Copy immediately! You won't be able to see it again.

7. **Add API Permissions:**
   - Go to "API permissions"
   - Click "Add a permission" → "Microsoft Graph"
   - Select "Delegated permissions"
   - Add: `User.Read`, `email`, `profile`, `openid`
   - Click "Add permissions"

---

### 4. Discord OAuth Setup

#### Create Application

1. **Go to Discord Developer Portal:**
   - Visit: https://discord.com/developers/applications
   - Click "New Application"

2. **Create Application:**
   - Name: `Nova Voice`
   - Click "Create"

3. **Get Application Credentials:**
   - Go to "OAuth2" → "General"
   - Copy "Client ID" → Add to `gateway/.env` as `DISCORD_CLIENT_ID`
   - Copy "Client Secret" (click "Reset Secret" if needed) → Add to `gateway/.env` as `DISCORD_CLIENT_SECRET`

4. **Add Redirect URIs:**
   - Still in "OAuth2" → "General"
   - Under "Redirects", click "Add Redirect"
   - Add: `https://auth.nova-voice.com/auth/callback`
   - Optionally add: `http://localhost:8080/auth/callback` (for development)
   - Click "Save Changes"

5. **Configure OAuth2 Scopes:**
   - Go to "OAuth2" → "URL Generator"
   - Select scopes: `identify`, `email`
   - Copy the generated URL (optional, for testing)

---

## Environment File Template

After completing all OAuth setups, your `gateway/.env` file should look like this:

```bash
# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-at-least-32-characters-long

# Google OAuth
GOOGLE_CLIENT_ID=123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-AbCdEfGhIjKlMnOpQrStUvWxYz

# GitHub OAuth
GITHUB_CLIENT_ID=Iv1.abcdef1234567890
GITHUB_CLIENT_SECRET=abcdef1234567890abcdef1234567890abcdef12

# Microsoft/Azure OAuth
MICROSOFT_CLIENT_ID=12345678-1234-1234-1234-123456789012
MICROSOFT_CLIENT_SECRET=AbC~dEf1GhI2jKl3MnO4pQr5StU6vWx7YzA8bCd9
MICROSOFT_TENANT_ID=common

# Discord OAuth
DISCORD_CLIENT_ID=123456789012345678
DISCORD_CLIENT_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

---

## Testing OAuth Flow

### Test Each Provider Locally First

1. **Start your gateway:**
   ```bash
   cd infra
   docker-compose up gateway
   ```

2. **Test OAuth endpoints:**
   - Google: `http://localhost:8080/auth/google`
   - GitHub: `http://localhost:8080/auth/github`
   - Microsoft: `http://localhost:8080/auth/microsoft`
   - Discord: `http://localhost:8080/auth/discord`

3. **Verify Callback Works:**
   - After authenticating, you should be redirected to the callback URL
   - Check gateway logs for authentication success/failure

### Test Production OAuth

After deploying:

1. **Launch Nova Voice application** (production build)
2. **Click "Login"**
3. **Select OAuth provider** (Google, GitHub, Microsoft, or Discord)
4. **Complete authentication** in browser
5. **Verify redirect** back to application
6. **Check user is logged in** in the app

---

## Common Issues & Solutions

### "Redirect URI Mismatch" Error

**Problem:** OAuth provider shows "redirect_uri_mismatch" error

**Solutions:**
1. Verify EXACT match: `https://auth.nova-voice.com/auth/callback`
2. Check for trailing slashes (shouldn't have one)
3. Ensure protocol is `https://` (not `http://`)
4. Wait a few minutes after adding redirect URI (some providers cache)

### "Invalid Client" Error

**Problem:** OAuth provider shows "invalid_client" error

**Solutions:**
1. Verify Client ID is correct in `gateway/.env`
2. Verify Client Secret is correct (no extra spaces)
3. Check if OAuth app is enabled in provider console
4. For Microsoft: Ensure you're using the correct tenant ID

### CORS Errors in Browser

**Problem:** Browser shows CORS policy errors during OAuth

**Solutions:**
1. Verify Cloudflare Tunnel is routing correctly to port 8080
2. Check that gateway is running: `docker-compose ps`
3. Ensure `auth.nova-voice.com` DNS is configured
4. Test API health: `curl https://api.nova-voice.com/health`

### JWT Token Issues

**Problem:** Authentication succeeds but token validation fails

**Solutions:**
1. Verify `JWT_SECRET` is set in `gateway/.env`
2. Ensure `JWT_SECRET` is at least 32 characters long
3. Generate strong secret: `openssl rand -base64 32`
4. Restart gateway after changing JWT_SECRET

---

## Security Best Practices

1. **Client Secrets:**
   - Never commit `.env` files to git
   - Use different credentials for development vs production
   - Rotate secrets periodically (every 6-12 months)

2. **JWT Secret:**
   - Use cryptographically random string (32+ characters)
   - Never share or expose publicly
   - Different secret for dev/staging/production

3. **OAuth Apps:**
   - Enable only required scopes (principle of least privilege)
   - Monitor OAuth app usage in provider consoles
   - Revoke unused apps/tokens regularly

4. **Redirect URIs:**
   - Only add legitimate redirect URIs
   - Use HTTPS for all production URIs
   - Remove development URIs from production OAuth apps

---

## Verification Checklist

- [ ] Google OAuth app created with correct redirect URI
- [ ] GitHub OAuth app created with correct redirect URI
- [ ] Microsoft app registration created with correct redirect URI
- [ ] Discord application created with correct redirect URI
- [ ] All credentials added to `gateway/.env`
- [ ] JWT_SECRET generated and added to `gateway/.env`
- [ ] `.env` file is in `.gitignore`
- [ ] OAuth flow tested locally (development)
- [ ] OAuth flow tested in production (after deployment)
- [ ] All providers working correctly

---

**Need Help?**

If you encounter issues:
1. Check gateway logs: `docker-compose logs gateway`
2. Verify environment variables are loaded: Add `console.log(process.env.GOOGLE_CLIENT_ID)` temporarily
3. Test each provider individually
4. Ensure Cloudflare DNS and tunnel are properly configured


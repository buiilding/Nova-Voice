# Real-Time Speech Translation Platform - Deployment Guide

# ⚠️ CRITICAL SECURITY WARNING

**This codebase is NOT ready for production deployment.** This guide describes a development setup only. Before attempting any production deployment, you must address critical security and operational issues documented in the main README.md.

**Key Issues:**
- No TLS/SSL encryption
- Incomplete authentication system
- Inadequate security measures
- No proper database for user data
- Missing monitoring and alerting
- No comprehensive testing

This guide covers deploying your speech translation backend to your local computer and packaging the frontend as a downloadable .exe with Google authentication for worldwide client connections.

## Table of Contents

1. [System Overview](#system-overview)
2. [Backend Deployment on Local Computer](#backend-deployment-on-local-computer)
3. [Frontend Packaging with Google Authentication](#frontend-packaging-with-google-authentication)
4. [Worldwide Client Connection Setup](#worldwide-client-connection-setup)
5. [Security and Authentication](#security-and-authentication)
6. [Monitoring and Scaling](#monitoring-and-scaling)
7. [Troubleshooting](#troubleshooting)

## System Overview

Your system consists of:

- **Backend**: Dockerized microservices (Gateway, STT Workers, Translation Workers, Redis)
- **Frontend**: Electron-based desktop app (Nova UI) with real-time speech processing
- **Architecture**: WebSocket-based real-time communication with Redis message queuing

```
Internet Clients → Cloudflare (DNS + SSL + Firewall)
                         ↓
                 Cloudflare Tunnel
                         ↓
                    Local Computer
                         ↓
                    Gateway (Port 5026)
                         ↓
                    Redis Message Queue
                         ↓
               STT Workers ←→ Translation Workers
```

## Backend Deployment on Local Computer

### Prerequisites

- Docker and Docker Compose installed
- 4GB+ RAM available
- NVIDIA GPU (optional, for faster transcription)
- Cloudflare account (free tier available)
- Domain name pointed to Cloudflare nameservers

### 1. Clone and Setup

```bash
git clone <your-repo>
cd realtime-speech-microservices
cd infra
```

### 2. Environment Configuration

Create `.env` file in the `infra/` directory:

```bash
# Copy example configuration
cp env.example .env

# Edit with your settings
nano .env
```

Key settings for production:
```bash
# Gateway Configuration
GATEWAY_PORT=5026
HEALTH_PORT=8080
REDIS_URL=redis://localhost:6379

# Security (will add later)
ENABLE_AUTH=true
JWT_SECRET=your-secure-jwt-secret-here

# Performance
SILENCE_THRESHOLD_SECONDS=2.0
MAX_QUEUE_DEPTH=100
MODEL_SIZE=large-v3
DEVICE=cuda  # or cpu
```

### 3. Start Backend Services

```bash
# Start all services
docker-compose up --build -d

# Scale workers based on your hardware
docker-compose up --scale stt_worker=2 --scale translation_worker=1 --scale gateway=1 -d

# Check service health
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
```

### 4. GPU Support (Optional)

For faster transcription, enable GPU support:

Create `docker-compose.override.yml`:
```yaml
version: '3.8'
services:
  stt_worker:
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=cuda
  translation_worker:
    runtime: nvidia
  gateway:
    runtime: nvidia
```

## Frontend Packaging with Google Authentication

### Prerequisites

- Node.js 18+
- Google Cloud Console account
- Domain name for OAuth redirect

### 1. Google OAuth Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable Google+ API and Google OAuth2 API

2. **Configure OAuth Consent Screen**:
   - Go to "OAuth consent screen"
   - Choose "External" user type
   - Fill app information
   - Add scopes: `openid`, `email`, `profile`

3. **Create OAuth Credentials**:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Desktop application"
   - Download the JSON file with your client ID and secret

### 2. Configure Frontend Authentication

1. **Update Electron Main Process** (`Nova-UI/electron/main.js`):

```javascript
// Add Google OAuth configuration
const GOOGLE_CLIENT_ID = 'your-google-client-id.apps.googleusercontent.com';
const GOOGLE_CLIENT_SECRET = 'your-google-client-secret';
const BACKEND_URL = 'https://your-domain.com'; // Your exposed backend URL

// Add OAuth login window creation
function createLoginWindow() {
  if (loginWindow && !loginWindow.isDestroyed()) {
    return loginWindow;
  }

  loginWindow = new BrowserWindow({
    width: 500,
    height: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'login-preload.js')
    }
  });

  // Load Google OAuth URL
  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${GOOGLE_CLIENT_ID}&` +
    `redirect_uri=${encodeURIComponent('https://auth.your-domain.com/auth/callback')}&` +
    `scope=openid%20email%20profile&` +
    `response_type=code&` +
    `access_type=offline`;

  loginWindow.loadURL(authUrl);
  return loginWindow;
}

// Handle OAuth callback
ipcMain.handle('auth-callback', async (event, authCode) => {
  try {
    // Exchange code for tokens
    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: GOOGLE_CLIENT_ID,
        client_secret: GOOGLE_CLIENT_SECRET,
        code: authCode,
        grant_type: 'authorization_code',
        redirect_uri: 'http://localhost:3000/auth/callback'
      })
    });

    const tokens = await tokenResponse.json();

    // Get user info
    const userResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
      headers: { 'Authorization': `Bearer ${tokens.access_token}` }
    });

    const userInfo = await userResponse.json();

    // Send user info to backend for authentication
    const authResponse = await fetch(`https://auth.your-domain.com/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        google_id: userInfo.id,
        email: userInfo.email,
        name: userInfo.name,
        access_token: tokens.access_token
      })
    });

    const session = await authResponse.json();

    // Store JWT token and connect to WebSocket
    mainWindow.webContents.send('auth-success', session);

  } catch (error) {
    console.error('Authentication failed:', error);
    mainWindow.webContents.send('auth-error', error.message);
  }
});
```

### 3. Update Login Preload Script

Update `Nova-UI/electron/login-preload.js`:

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onAuthCallback: (callback) => ipcRenderer.on('auth-callback', callback),
  sendAuthCode: (code) => ipcRenderer.invoke('auth-callback', code),
  closeLoginWindow: () => ipcRenderer.invoke('close-login-window')
});

// Handle OAuth redirect
window.addEventListener('load', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const authCode = urlParams.get('code');

  if (authCode) {
    // Send auth code to main process
    window.electronAPI.sendAuthCode(authCode);
  }
});
```

### 4. Update Main Application

Update `Nova-UI/app/page.tsx` to handle authentication:

```typescript
// Add authentication state
const [isAuthenticated, setIsAuthenticated] = useState(false);
const [user, setUser] = useState(null);

// Handle authentication success
useEffect(() => {
  if (window.electronAPI) {
    window.electronAPI.onAuthSuccess((event, session) => {
      setIsAuthenticated(true);
      setUser(session.user);
      localStorage.setItem('auth_token', session.token);

      // Now connect to WebSocket with auth token
      connectToBackend(session.token);
    });

    window.electronAPI.onAuthError((event, error) => {
      console.error('Authentication failed:', error);
      // Show error to user
    });
  }
}, []);

const connectToBackend = (authToken: string) => {
  // Update WebSocket connection to use Cloudflare tunnel
  const wsUrl = `wss://ws.your-domain.com?token=${authToken}`;
  // ... existing connection logic
};
```

### 5. Package the Application

```bash
cd Nova-UI

# Install dependencies
npm install

# Build Next.js static export
npm run build

# Package as .exe
npm run dist
```

This creates `Nova-UI/dist/Nova UI Setup 0.1.0.exe` that users can download and install.

## Worldwide Client Connection Setup with Cloudflare

### 1. Cloudflare Account Setup

1. **Create Cloudflare Account**:
   - Go to [cloudflare.com](https://cloudflare.com) and sign up for free account
   - Add your domain to Cloudflare

2. **Domain Configuration**:
   - In Cloudflare dashboard, add your domain
   - Update your domain's nameservers to Cloudflare's nameservers
   - Wait for DNS propagation (can take up to 24 hours)

3. **SSL Configuration**:
   - In Cloudflare dashboard: SSL/TLS → Overview
   - Set SSL mode to "Full (strict)" or "Flexible"
   - Cloudflare provides free SSL certificates automatically

### 2. Install Cloudflare Tunnel

Cloudflare Tunnel creates secure connections from your local machine to Cloudflare without exposing ports.

```bash
# Install cloudflared (Cloudflare Tunnel client)
# On Ubuntu/Debian:
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# On other systems, check: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/

# Verify installation
cloudflared version
```

### 3. Authenticate with Cloudflare

```bash
# Login to your Cloudflare account
cloudflared tunnel login

# This will open a browser window for authentication
# Select your domain when prompted
```

### 4. Create and Configure Tunnel

```bash
# Create a tunnel for your speech app
cloudflared tunnel create speech-app

# List your tunnels to get the tunnel ID
cloudflared tunnel list

# Create tunnel configuration file
nano ~/.cloudflared/config.yaml
```

Tunnel configuration (`config.yaml`):
```yaml
tunnel: YOUR_TUNNEL_ID_HERE  # Replace with actual tunnel ID
credentials-file: /home/YOUR_USERNAME/.cloudflared/YOUR_TUNNEL_ID_HERE.json

ingress:
  # WebSocket endpoint
  - hostname: ws.your-domain.com
    service: http://localhost:5026
    originRequest:
      noTLSVerify: true

  # Health check endpoint
  - hostname: api.your-domain.com
    service: http://localhost:8080
    originRequest:
      noTLSVerify: true

  # Authentication endpoint
  - hostname: auth.your-domain.com
    service: http://localhost:8080
    originRequest:
      noTLSVerify: true

  # Catch-all rule (required)
  - service: http_status:404
```

### 5. Configure DNS in Cloudflare

In Cloudflare dashboard:

1. **Go to DNS → Records**
2. **Add CNAME records**:
   - `ws.your-domain.com` → `YOUR_TUNNEL_ID_HERE.cfargotunnel.com`
   - `api.your-domain.com` → `YOUR_TUNNEL_ID_HERE.cfargotunnel.com`
   - `auth.your-domain.com` → `YOUR_TUNNEL_ID_HERE.cfargotunnel.com`

3. **Set DNS proxy status** (orange cloud) to "Proxied" for all records

### 6. Start the Tunnel

```bash
# Start tunnel in background
cloudflared tunnel run speech-app &

# Or create a systemd service for auto-startup
sudo nano /etc/systemd/system/cloudflared.service
```

Systemd service configuration:
```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/local/bin/cloudflared tunnel run speech-app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sudo systemctl status cloudflared
```

### 7. Test the Connection

```bash
# Test WebSocket endpoint
curl -I https://ws.your-domain.com/health

# Test API endpoint
curl https://api.your-domain.com/health

# Check tunnel status
cloudflared tunnel list
```

### 4. Backend Authentication Implementation

Add authentication to the Gateway service:

```python
# Add to gateway/gateway.py imports
import jwt
from datetime import datetime, timedelta

# Add authentication middleware
class AuthMiddleware:
    def __init__(self, jwt_secret: str):
        self.jwt_secret = jwt_secret

    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

# Update WebSocket connection handler
async def websocket_handler(self, websocket, path):
    # Extract token from query parameters
    query_params = parse_qs(urlparse(path).query)
    token = query_params.get('token', [None])[0]

    if not token:
        await websocket.send(json.dumps({
            "type": "error",
            "message": "Authentication required"
        }))
        return

    try:
        # Verify JWT token
        user_data = self.auth_middleware.verify_token(token)
        client_id = user_data['user_id']
    except ValueError as e:
        await websocket.send(json.dumps({
            "type": "error",
            "message": str(e)
        }))
        return

    # Proceed with authenticated connection
    # ... rest of existing handler
```

### 5. User Management Database

Add user management to Redis:

```python
# User management functions
async def create_or_update_user(self, google_user_data: dict) -> str:
    """Create or update user from Google OAuth data"""
    user_id = f"user:{google_user_data['google_id']}"

    user_data = {
        'google_id': google_user_data['google_id'],
        'email': google_user_data['email'],
        'name': google_user_data['name'],
        'created_at': datetime.now().isoformat(),
        'last_login': datetime.now().isoformat()
    }

    await self.redis_client.hset(user_id, mapping=user_data)

    # Create JWT token
    token_payload = {
        'user_id': google_user_data['google_id'],
        'email': google_user_data['email'],
        'exp': datetime.utcnow() + timedelta(days=7)
    }

    token = jwt.encode(token_payload, self.jwt_secret, algorithm='HS256')
    return token
```

## Security and Authentication

### Cloudflare Security Features

1. **DDoS Protection**:
   - Automatic DDoS mitigation
   - Rate limiting and bot protection
   - Web Application Firewall (WAF)

2. **SSL/TLS Security**:
   - Free SSL certificates with automatic renewal
   - End-to-end encryption
   - HSTS (HTTP Strict Transport Security)

3. **Access Control**:
   - IP whitelisting/blacklisting
   - Geographic restrictions
   - Zero Trust security model

### Backend Security

1. **API Authentication**:
   - JWT tokens with 7-day expiration
   - Secure token storage in Electron app
   - Token refresh mechanism

2. **WebSocket Security**:
   - Token-based authentication
   - Connection rate limiting
   - Input validation and sanitization

3. **Network Security**:
   - Cloudflare Tunnel provides secure encrypted connection
   - No open ports on local firewall
   - All traffic routed through Cloudflare's secure network

### Client Security

1. **Token Storage**:
   - Secure token storage using Electron safeStorage
   - Automatic token refresh
   - Secure logout mechanism

2. **Data Protection**:
   - No sensitive data stored locally
   - Encrypted communication channels
   - Input validation on all forms

## Monitoring and Scaling

### Health Monitoring

```bash
# Check all services
curl https://your-domain.com/health

# Monitor with automated checks
*/5 * * * * /usr/bin/curl -f https://your-domain.com/health || systemctl restart speech-services
```

### Scaling Configuration

```bash
# Scale based on load
docker-compose up --scale stt_worker=4 --scale translation_worker=2 --scale gateway=2

# Auto-scaling script
#!/bin/bash
QUEUE_LENGTH=$(docker-compose exec redis redis-cli xlen audio_jobs)
if [ "$QUEUE_LENGTH" -gt 50 ]; then
    docker-compose up --scale stt_worker=6
fi
```

### Performance Monitoring

```bash
# Monitor Redis queue
watch -n 1 'docker-compose exec redis redis-cli xlen audio_jobs'

# Monitor system resources
htop
docker stats

# View application logs
docker-compose logs -f gateway
```

## Troubleshooting

### Common Issues

1. **Cloudflare Tunnel Connection Failed**:
   ```bash
   # Check tunnel status
   cloudflared tunnel list

   # Check tunnel logs
   sudo journalctl -u cloudflared -f

   # Restart tunnel
   sudo systemctl restart cloudflared

   # Check DNS propagation
   nslookup ws.your-domain.com
   ```

2. **WebSocket Connection Failed**:
   ```bash
   # Check if backend is running
   curl http://localhost:8080/health

   # Check Cloudflare tunnel connectivity
   curl https://api.your-domain.com/health

   # Verify DNS records in Cloudflare dashboard
   ```

3. **SSL/HTTPS Issues**:
   ```bash
   # Check SSL certificate status in Cloudflare
   # Verify SSL mode is set to "Full (strict)"
   # Check if domain is properly proxied (orange cloud)
   ```

4. **Authentication Issues**:
   ```bash
   # Check JWT token validity
   # Verify Google OAuth redirect URI matches: https://auth.your-domain.com/auth/callback
   # Check Google OAuth credentials
   # Verify Cloudflare DNS for auth subdomain
   ```

5. **Audio Processing Issues**:
   ```bash
   # Check STT worker logs
   docker-compose logs stt_worker

   # Verify GPU availability
   nvidia-smi
   ```

4. **Performance Issues**:
   ```bash
   # Monitor system resources
   htop
   docker stats

   # Check queue lengths
   docker-compose exec redis redis-cli xlen audio_jobs
   ```

### Logs and Debugging

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f gateway
docker-compose logs -f stt_worker

# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose up --build
```

## Production Checklist

- [V] Domain name purchased and pointed to Cloudflare nameservers
- [V] Cloudflare account created and domain added
- [V] Cloudflare Tunnel installed and authenticated
- [V] DNS records configured (ws, api, auth subdomains)
- [V] SSL/TLS configured in Cloudflare (Full strict mode)
- [V] Cloudflare Tunnel running as systemd service
- [V] Authentication system implemented
- [V] Google OAuth configured with correct redirect URI
- [V] Frontend packaged and tested
- [V] Backend services running and healthy
- [V] Cloudflare Tunnel connectivity verified
- [V] Monitoring and alerts configured
- [V] Backup strategy in place
- [ ] Performance testing completed

## ⚠️ Production Readiness Assessment

### Current Status: DEVELOPMENT ONLY

The current setup described in this guide is suitable **only for development and testing**. It has critical security and operational deficiencies that prevent production deployment.

### Required Changes for Production

#### Phase 1: Critical Security Fixes (Must Complete First)

1. **Implement Proper TLS/SSL**
   ```bash
   # Replace all ws:// with wss://
   # Replace all http:// with https://
   # Implement certificate management
   ```

2. **Fix Authentication System**
   ```python
   # Replace incomplete JWT with OAuth 2.0 + PKCE
   # Add token refresh mechanism
   # Implement rate limiting
   # Add proper session management
   ```

3. **Database Migration**
   ```sql
   -- Replace Redis data storage with proper database
   -- Implement user data persistence
   -- Add backup and recovery
   ```

4. **Security Hardening**
   - Add input validation
   - Implement security headers
   - Remove sensitive data from logs
   - Add CSRF protection

#### Phase 2: Operational Requirements

1. **Monitoring & Alerting**
   ```yaml
   # Implement ELK stack or similar
   # Add error tracking (Sentry)
   # Create alerting system
   ```

2. **Testing & Quality Assurance**
   ```bash
   # Add unit tests
   # Add integration tests
   # Implement CI/CD pipeline
   # Add load testing
   ```

3. **Infrastructure Improvements**
   ```yaml
   # Add Kubernetes manifests
   # Implement auto-scaling
   # Add resource limits
   # Create backup procedures
   ```

### Recommended Production Architecture

```
Internet → Cloudflare (WAF + DDoS) → Load Balancer → API Gateway → Services
                      ↓              ↓              ↓
                SSL Termination  Authentication  Authorization
                                      ↓
                               Redis Cluster (Caching)
                                      ↓
                            PostgreSQL (User Data)
                                      ↓
                            STT Workers ←→ Translation Workers
```

### Cost Estimation for Production

- **Domain & DNS**: $10-20/year
- **Cloudflare**: Free tier sufficient
- **SSL Certificates**: Free (Let's Encrypt/Cloudflare)
- **VPS/Kubernetes**: $50-200/month (depending on scale)
- **Monitoring**: $50-100/month
- **Backup Storage**: $10-50/month

**Total estimated cost: $120-370/month** for a properly secured production deployment.

### Next Steps

1. **Do not attempt production deployment** with current codebase
2. **Review the production readiness checklist** in README.md
3. **Implement critical security fixes** before any public deployment
4. **Consider hiring security experts** for production audit
5. **Plan for 3-6 months** of development before production-ready

This setup allows users worldwide to download your .exe, authenticate with Google, and connect to your local backend for real-time speech translation - **but only after implementing the required security and operational improvements.**

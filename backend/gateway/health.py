"""
health.py - Health monitoring and metrics for the Gateway service

Provides HTTP health check endpoints and comprehensive metrics collection.
Handles CORS setup and server lifecycle management.
"""

import time
import logging
import json
from aiohttp import web
import aiohttp_cors

from config import HEALTH_PORT, MAX_QUEUE_DEPTH


class HealthMonitor:
    """Handles health monitoring and metrics endpoints"""

    def __init__(self, instance_id: str, logger: logging.Logger, redis_client, gateway_service):
        self.instance_id = instance_id
        self.logger = logger
        self.redis_client = redis_client
        self.gateway_service = gateway_service

    async def health_check_handler(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "instance_id": self.instance_id,
            "timestamp": time.time(),
            "metrics": self.gateway_service.metrics
        })

    async def metrics_handler(self, request):
        """Metrics endpoint"""
        # Get Redis queue depth using RedisClient
        queue_depth = await self.redis_client.get_queue_depth()

        return web.json_response({
            "instance_id": self.instance_id,
            "queue_depth": queue_depth,
            "max_queue_depth": MAX_QUEUE_DEPTH,
            "metrics": self.gateway_service.metrics,
            "timestamp": time.time()
        })

    async def auth_oauth_handler(self, request, provider: str):
        """Generic OAuth authentication endpoint for all providers"""
        try:
            data = await request.json()

            # Validate required fields
            provider_id_field = f"{provider}_id"
            required_fields = [provider_id_field, 'email', 'name', 'access_token']
            for field in required_fields:
                if field not in data:
                    return web.json_response(
                        {"success": False, "error": f"Missing required field: {field}"},
                        status=400
                    )

            # Create or update user and generate JWT token
            token = await self.gateway_service.create_or_update_user(data)

            return web.json_response({
                "success": True,
                "token": token,
                "user": {
                    provider_id_field: data[provider_id_field],
                    "email": data['email'],
                    "name": data['name']
                }
            })

        except Exception as e:
            self.logger.error(f"{provider.title()} authentication error: {e}")
            return web.json_response(
                {"success": False, "error": f"{provider.title()} authentication failed"},
                status=500
            )

    async def auth_google_handler(self, request):
        """Google OAuth authentication endpoint"""
        return await self.auth_oauth_handler(request, "google")

    async def auth_github_handler(self, request):
        """GitHub OAuth authentication endpoint"""
        return await self.auth_oauth_handler(request, "github")

    async def auth_microsoft_handler(self, request):
        """Microsoft OAuth authentication endpoint"""
        return await self.auth_oauth_handler(request, "microsoft")

    async def auth_discord_handler(self, request):
        """Discord OAuth authentication endpoint"""
        return await self.auth_oauth_handler(request, "discord")

    async def auth_callback_handler(self, request):
        """OAuth callback endpoint for handling OAuth redirects"""
        try:
            import time as time_module
            callback_start = time_module.time()

            # Extract authorization code and provider from query parameters
            code = request.query.get('code')
            state = request.query.get('state', '')
            provider = 'google'  # Default to google for backward compatibility

            # Parse provider from state parameter (format: provider=github)
            if state and '=' in state:
                state_parts = state.split('=')
                if len(state_parts) == 2 and state_parts[0] == 'provider':
                    provider = state_parts[1]

            self.logger.info(f"[AUTH_CALLBACK] Received callback for provider: {provider}")

            if not code:
                return web.json_response(
                    {"success": False, "error": "Authorization code not provided"},
                    status=400
                )

            # Handle different providers
            oauth_start = time_module.time()
            if provider == 'google':
                user_data, provider_name = await self._handle_google_oauth(code)
            elif provider == 'github':
                user_data, provider_name = await self._handle_github_oauth(code)
            elif provider == 'microsoft':
                user_data, provider_name = await self._handle_microsoft_oauth(code)
            elif provider == 'discord':
                user_data, provider_name = await self._handle_discord_oauth(code)
            else:
                return web.json_response(
                    {"success": False, "error": f"Unsupported provider: {provider}"},
                    status=400
                )

            oauth_end = time_module.time()
            self.logger.info(f"[AUTH_CALLBACK] OAuth exchange took {oauth_end - oauth_start:.2f}s")

            # Create or update user and generate JWT token
            jwt_start = time_module.time()
            token = await self.gateway_service.create_or_update_user(user_data)
            jwt_end = time_module.time()
            self.logger.info(f"[AUTH_CALLBACK] JWT creation took {jwt_end - jwt_start:.2f}s")

            # Store authentication result temporarily in Redis for polling
            redis_start = time_module.time()
            auth_key = f"auth_session:latest"
            auth_data = {
                'token': token,
                'user': {
                    'id': user_data[f'{provider}_id'],
                    'email': user_data['email'],
                    'name': user_data['name']
                },
                'timestamp': int(time.time())
            }
            await self.redis_client.redis.setex(auth_key, 300, json.dumps(auth_data).encode('utf-8'))  # Expire in 5 minutes
            redis_end = time_module.time()
            self.logger.info(f"[AUTH_CALLBACK] Redis storage took {redis_end - redis_start:.2f}s")

            callback_end = time_module.time()
            self.logger.info(f"[AUTH_CALLBACK] Total callback processing: {callback_end - callback_start:.2f}s")

            # Return HTML page that shows success
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    :root {{
                        --background: oklch(0.145 0 0);
                        --foreground: oklch(0.985 0 0);
                        --card: oklch(0.145 0 0);
                        --primary: oklch(0.6 0.12 240);
                        --primary-foreground: oklch(0.985 0 0);
                        --border: oklch(0.269 0 0);
                        --radius: 0.625rem;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                        background-color: var(--background);
                        color: var(--foreground);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                        padding: 20px;
                        box-sizing: border-box;
                    }}
                    .container {{
                        position: relative;
                        width: 100%;
                        max-width: 480px;
                        background-color: var(--card);
                        border: 1px solid var(--border);
                        border-radius: var(--radius);
                        padding: 48px;
                        text-align: center;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                        overflow: hidden;
                    }}
                    .glow {{
                        position: absolute;
                        top: 0;
                        left: 50%;
                        transform: translateX(-50%);
                        width: 200%;
                        height: 200px;
                        background: radial-gradient(circle, oklch(0.6 0.12 240 / 0.15), transparent 60%);
                        pointer-events: none;
                        z-index: 0;
                    }}
                    .content {{
                        position: relative;
                        z-index: 1;
                    }}
                    .icon {{
                        font-size: 48px;
                        line-height: 1;
                        margin-bottom: 24px;
                    }}
                    h1 {{
                        font-size: 24px;
                        font-weight: 600;
                        margin: 0 0 12px;
                    }}
                    p {{
                        color: oklch(0.708 0 0);
                        margin: 0 0 32px;
                        font-size: 16px;
                        line-height: 1.6;
                    }}
                    .close-btn {{
                        background-color: var(--primary);
                        color: var(--primary-foreground);
                        border: none;
                        border-radius: calc(var(--radius) - 2px);
                        padding: 12px 24px;
                        font-size: 16px;
                        font-weight: 500;
                        cursor: pointer;
                        transition: background-color 0.2s ease;
                        width: 100%;
                    }}
                    .close-btn:hover {{
                        background-color: oklch(0.6 0.12 240 / 0.9);
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="glow"></div>
                    <div class="content">
                        <div class="icon">🚀</div>
                        <h1>Authentication Successful</h1>
                        <p>You've successfully connected with {provider_name}. You can now close this window and return to Nova app.</p>
                        <button class="close-btn" onclick="window.close()">Close Window</button>
                    </div>
                </div>
                <script>
                    setTimeout(() => {{
                        window.close();
                    }}, 5000);
                </script>
            </body>
            </html>
            """

            return web.Response(
                text=html_content,
                content_type='text/html',
                headers={'Cache-Control': 'no-cache'}
            )

        except Exception as e:
            self.logger.error(f"OAuth callback error: {e}")
            return web.json_response(
                {"success": False, "error": "OAuth callback failed"},
                status=500
            )

    async def _handle_oauth(self, code: str, provider_config: dict):
        """Generic OAuth token exchange and user info retrieval"""
        import aiohttp
        import os

        provider_name = provider_config['name']
        client_id = os.getenv(provider_config['client_id_env'])
        client_secret = os.getenv(provider_config['client_secret_env'])

        if not client_id or not client_secret:
            raise ValueError(f"{provider_name} OAuth credentials not configured")

        # Exchange code for tokens
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': os.getenv('OAUTH_REDIRECT_URI', 'https://auth.nova-voice.com/auth/callback')
        }

        # Add provider-specific token data
        if 'token_data_extra' in provider_config:
            token_data.update(provider_config['token_data_extra'])

        async with aiohttp.ClientSession() as session:
            # Token exchange
            token_url = provider_config['token_url']
            token_headers = provider_config.get('token_headers', {})

            self.logger.info(f"[OAUTH] Exchanging code with {provider_name}...")
            token_start = time.time()
            async with session.post(token_url, headers=token_headers, data=token_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"{provider_name} token exchange failed: {error_text}")

                tokens = await response.json()
                access_token = tokens.get('access_token')
                if not access_token:
                    raise Exception(f"No access token received from {provider_name}")

                token_end = time.time()
                self.logger.info(f"[OAUTH] Token exchange took {token_end - token_start:.2f}s")

            # Get user info
            user_info_url = provider_config['user_info_url']
            user_info_headers = provider_config['user_info_headers'].copy()
            user_info_headers['Authorization'] = user_info_headers['Authorization'].format(access_token=access_token)

            self.logger.info(f"[OAUTH] Fetching user info from {provider_name}...")
            userinfo_start = time.time()
            async with session.get(user_info_url, headers=user_info_headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to get user info from {provider_name}")
                user_info = await response.json()

                userinfo_end = time.time()
                self.logger.info(f"[OAUTH] User info fetch took {userinfo_end - userinfo_start:.2f}s")

            # Handle provider-specific additional requests (like GitHub emails)
            if 'additional_requests' in provider_config:
                for req_config in provider_config['additional_requests']:
                    req_headers = req_config['headers'].copy()
                    req_headers['Authorization'] = req_headers['Authorization'].format(access_token=access_token)

                    async with session.get(req_config['url'], headers=req_headers) as response:
                        if response.status == 200:
                            additional_data = await response.json()
                            # Apply transformation function
                            if 'transform' in req_config:
                                req_config['transform'](user_info, additional_data)

            # Build user data using provider-specific mapping
            user_data = {
                'access_token': access_token
            }

            for field, mapping in provider_config['user_data_mapping'].items():
                if callable(mapping):
                    user_data[field] = mapping(user_info)
                else:
                    user_data[field] = user_info.get(mapping, '')

            return user_data, provider_name

    async def _handle_google_oauth(self, code):
        """Handle Google OAuth token exchange and user info retrieval"""
        return await self._handle_oauth(code, {
            'name': 'Google',
            'client_id_env': 'GOOGLE_CLIENT_ID',
            'client_secret_env': 'GOOGLE_CLIENT_SECRET',
            'token_url': 'https://oauth2.googleapis.com/token',
            'user_info_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
            'user_info_headers': {'Authorization': 'Bearer {access_token}'},
            'user_data_mapping': {
                'google_id': 'id',
                'email': 'email',
                'name': 'name'
            }
        })

    async def _handle_github_oauth(self, code):
        """Handle GitHub OAuth token exchange and user info retrieval"""
        def email_transform(user_info, emails):
            primary_email = next((email for email in emails if email.get('primary')), None)
            if primary_email:
                user_info['email'] = primary_email['email']

        return await self._handle_oauth(code, {
            'name': 'GitHub',
            'client_id_env': 'GITHUB_CLIENT_ID',
            'client_secret_env': 'GITHUB_CLIENT_SECRET',
            'token_url': 'https://github.com/login/oauth/access_token',
            'token_headers': {'Accept': 'application/json'},
            'user_info_url': 'https://api.github.com/user',
            'user_info_headers': {
                'Authorization': 'Bearer {access_token}',
                'User-Agent': 'Nova-Voice-App'
            },
            'additional_requests': [{
                'url': 'https://api.github.com/user/emails',
                'headers': {
                    'Authorization': 'Bearer {access_token}',
                    'User-Agent': 'Nova-Voice-App'
                },
                'transform': email_transform
            }],
            'user_data_mapping': {
                'github_id': 'id',
                'email': lambda ui: ui.get('email', ''),
                'name': lambda ui: ui.get('name') or ui.get('login', ''),
                'avatar': lambda ui: ui.get('avatar_url', '')
            }
        })

    async def _handle_microsoft_oauth(self, code):
        """Handle Microsoft OAuth token exchange and user info retrieval"""
        import os
        tenant_id = os.getenv('MICROSOFT_TENANT_ID', 'common')

        return await self._handle_oauth(code, {
            'name': 'Microsoft',
            'client_id_env': 'MICROSOFT_CLIENT_ID',
            'client_secret_env': 'MICROSOFT_CLIENT_SECRET',
            'token_url': f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
            'user_info_url': 'https://graph.microsoft.com/v1.0/me',
            'user_info_headers': {'Authorization': 'Bearer {access_token}'},
            'user_data_mapping': {
                'microsoft_id': 'id',
                'email': lambda ui: ui.get('mail') or ui.get('userPrincipalName', ''),
                'name': lambda ui: ui.get('displayName', '')
            }
        })

    async def _handle_discord_oauth(self, code):
        """Handle Discord OAuth token exchange and user info retrieval"""
        return await self._handle_oauth(code, {
            'name': 'Discord',
            'client_id_env': 'DISCORD_CLIENT_ID',
            'client_secret_env': 'DISCORD_CLIENT_SECRET',
            'token_url': 'https://discord.com/api/oauth2/token',
            'user_info_url': 'https://discord.com/api/users/@me',
            'user_info_headers': {'Authorization': 'Bearer {access_token}'},
            'user_data_mapping': {
                'discord_id': 'id',
                'email': lambda ui: ui.get('email', ''),
                'name': lambda ui: ui.get('username', ''),
                'avatar': lambda ui: ui.get('avatar') and f"https://cdn.discordapp.com/avatars/{ui['id']}/{ui['avatar']}.png" or ''
            }
        })

    async def auth_status_handler(self, request):
        """Check if authentication was recently completed"""
        try:
            auth_key = f"auth_session:latest"
            auth_data_json = await self.redis_client.redis.get(auth_key)
            self.logger.info(f"[AUTH_STATUS] Polling check - key exists: {auth_data_json is not None}")

            if auth_data_json:
                # Decode bytes to string if needed
                if isinstance(auth_data_json, bytes):
                    auth_data_json = auth_data_json.decode('utf-8')
                auth_data = json.loads(auth_data_json)
                # Check if auth data is recent (within last 5 minutes to match Redis TTL)
                age = int(time.time()) - auth_data['timestamp']
                self.logger.info(f"[AUTH_STATUS] Auth data age: {age} seconds")
                if age < 300:  # 5 minutes = 300 seconds
                    self.logger.info(f"[AUTH_STATUS] ✓ Returning authenticated status for user: {auth_data['user'].get('email', 'unknown')}")
                    return web.json_response({
                        "authenticated": True,
                        "token": auth_data['token'],
                        "user": auth_data['user']
                    })

            self.logger.info("[AUTH_STATUS] ✗ Returning unauthenticated status")
            return web.json_response({"authenticated": False})

        except Exception as e:
            self.logger.error(f"Auth status error: {e}")
            return web.json_response(
                {"authenticated": False, "error": "Failed to check auth status"},
                status=500
            )

    async def auth_logout_handler(self, request):
        """Clear authentication session"""
        try:
            self.logger.info("Logout request received")
            auth_key = f"auth_session:latest"
            result = await self.redis_client.redis.delete(auth_key)
            self.logger.info(f"Deleted {result} auth keys from Redis")

            return web.json_response({"success": True})

        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return web.json_response(
                {"success": False, "error": "Failed to logout"},
                status=500
            )

    async def auth_validate_handler(self, request):
        """Validate JWT token"""
        try:
            # Get Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return web.json_response(
                    {"valid": False, "error": "No valid authorization header"},
                    status=401
                )

            token = auth_header.split(' ')[1]

            # Verify token using the gateway service's auth middleware
            try:
                payload = self.gateway_service.auth_middleware.verify_token(token)
                return web.json_response({
                    "valid": True,
                    "user_id": payload.get('user_id'),
                    "email": payload.get('email')
                })
            except Exception as e:
                return web.json_response(
                    {"valid": False, "error": str(e)},
                    status=401
                )

        except Exception as e:
            self.logger.error(f"Token validation error: {e}")
            return web.json_response(
                {"valid": False, "error": "Token validation failed"},
                status=500
            )

    async def discovery_least_loaded_handler(self, request):
        """Discovery endpoint for finding the least-loaded gateway"""
        try:
            # Get current metrics to determine load
            queue_depth = await self.redis_client.get_queue_depth()
            metrics = self.gateway_service.metrics

            # Determine gateway URL for clients
            import os
            # For tunnel setups: backend runs locally, but clients connect to public tunnel URL
            # Default to production tunnel URL, fallback to localhost for development
            gateway_url = os.getenv('GATEWAY_URL', 'wss://ws.nova-voice.com')

            # Extract port from gateway URL if it's a localhost URL
            port = 5026  # Default port
            if gateway_url.startswith('ws://localhost:'):
                try:
                    port = int(gateway_url.split(':')[-1])
                except (ValueError, IndexError):
                    port = 5026

            return web.json_response({
                "success": True,
                "gateway": {
                    "gateway_id": self.instance_id,
                    "port": port,
                    "ws_url": gateway_url,
                    "current_load": queue_depth,
                    "max_load": MAX_QUEUE_DEPTH
                }
            })

        except Exception as e:
            self.logger.error(f"Discovery least-loaded error: {e}")
            return web.json_response(
                {"success": False, "error": "Failed to discover gateway"},
                status=500
            )

    async def start_health_server(self):
        """Start health check HTTP server"""
        app = web.Application()
        app.router.add_get('/health', self.health_check_handler)
        app.router.add_get('/metrics', self.metrics_handler)
        app.router.add_get('/discovery/least-loaded', self.discovery_least_loaded_handler)

        # Disable aiohttp access logging
        logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

        # Add CORS support
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        for route in list(app.router.routes()):
            cors.add(route)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', HEALTH_PORT)
        await site.start()
        self.logger.info(f"Health server started on port {HEALTH_PORT}")

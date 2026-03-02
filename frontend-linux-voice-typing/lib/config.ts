// Configuration service that resolves URLs from environment variables or defaults
export const config = {
  gatewayUrl: process.env.GATEWAY_URL || 'ws://localhost:8081',
  backendUrl: process.env.BACKEND_URL || 'http://localhost:8080',
  debug: process.env.DEBUG === 'true',
};

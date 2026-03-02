const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

// Load .env file from the parent directory (Nova-UI/.env)
dotenv.config({ path: path.resolve(__dirname, '../.env') });

// Select the variables to expose in the production build
const envConfig = {
  NODE_ENV: 'production', // Hardcode to production for builds
  GATEWAY_URL: process.env.GATEWAY_URL,
  DISCOVERY_URL: process.env.DISCOVERY_URL,
  BACKEND_URL: process.env.BACKEND_URL,
  OAUTH_REDIRECT_URI: process.env.OAUTH_REDIRECT_URI,
  GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
  GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET,
  GITHUB_CLIENT_ID: process.env.GITHUB_CLIENT_ID,
  GITHUB_CLIENT_SECRET: process.env.GITHUB_CLIENT_SECRET,
  MICROSOFT_CLIENT_ID: process.env.MICROSOFT_CLIENT_ID,
  MICROSOFT_CLIENT_SECRET: process.env.MICROSOFT_CLIENT_SECRET,
  MICROSOFT_TENANT_ID: process.env.MICROSOFT_TENANT_ID,
  DISCORD_CLIENT_ID: process.env.DISCORD_CLIENT_ID,
  DISCORD_CLIENT_SECRET: process.env.DISCORD_CLIENT_SECRET,
};

// Write the config to a file that will be packaged with Electron
const outputPath = path.join(__dirname, '../electron/build-env.json');
fs.writeFileSync(outputPath, JSON.stringify(envConfig, null, 2));

console.log(`✅ Build environment config written to ${outputPath}`);

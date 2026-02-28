/**
 * Express.js Static File Server - For Performance Comparison
 *
 * Usage:
 *   PORT=3000 ROOT=./test_files node express-server.js
 */

const express = require('express');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;
const rootPath = process.env.ROOT || './test_files';

// Static file middleware
app.use('/static', express.static(rootPath, {
  maxAge: 3600000,  // 1 hour cache
  etag: false,      // Disable ETag for consistent benchmarking
  lastModified: false
}));

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// 404 handler
app.use((req, res) => {
  res.status(404).send('404 Not Found');
});

app.listen(port, () => {
  console.log(`[Express Server] ✅ listening on port ${port}`);
  console.log(`[Express Server] Root: ${rootPath}`);
  console.log(`[Express Server] URI: http://localhost:${port}/static/<filename>`);
});

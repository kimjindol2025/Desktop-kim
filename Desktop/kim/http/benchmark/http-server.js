/**
 * Node.js Native HTTP Server - For Performance Comparison
 *
 * Usage:
 *   PORT=3000 ROOT=./test_files node http-server.js
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const port = process.env.PORT || 3000;
const rootPath = process.env.ROOT || './test_files';

// MIME type detection
function getMimeType(filename) {
  const ext = path.extname(filename).toLowerCase();
  const mimeTypes = {
    '.html': 'text/html',
    '.htm': 'text/html',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.css': 'text/css',
    '.txt': 'text/plain',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.pdf': 'application/pdf',
    '.xml': 'text/xml'
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

const server = http.createServer((req, res) => {
  // Health check
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok' }));
    return;
  }

  // Static file serving
  if (req.method !== 'GET' || !req.url.startsWith('/static/')) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('404 Not Found');
    return;
  }

  // Extract filename
  const filename = req.url.substring(8);  // Remove '/static/'

  // Security: Block directory traversal
  if (filename.includes('..') || filename.startsWith('.')) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('403 Forbidden');
    return;
  }

  // Build full path
  const fullPath = path.join(rootPath, filename);

  // Verify path is within root
  const realRoot = path.resolve(rootPath);
  const realPath = path.resolve(fullPath);
  if (!realPath.startsWith(realRoot)) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('403 Forbidden');
    return;
  }

  // Read file
  fs.readFile(fullPath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }

    const mime = getMimeType(filename);
    res.writeHead(200, {
      'Content-Type': mime,
      'Content-Length': data.length,
      'Cache-Control': 'max-age=3600',
      'Connection': 'keep-alive'
    });
    res.end(data);
  });
});

server.listen(port, () => {
  console.log(`[Node.js HTTP Server] ✅ listening on port ${port}`);
  console.log(`[Node.js HTTP Server] Root: ${rootPath}`);
  console.log(`[Node.js HTTP Server] URI: http://localhost:${port}/static/<filename>`);
});

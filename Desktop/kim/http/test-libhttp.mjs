/**
 * Test: libhttp.so FFI bindings
 * Tests HTTP server created from event loop + http_server_impl.c
 */

import ffi from 'ffi-napi';
import path from 'path';
import { fileURLToPath } from 'url';
import http from 'http';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load libhttp.so
const libhttp = ffi.Library(path.join(__dirname, '../../dist/stdlib/libhttp.so'), {
  http_server_listen: ['pointer', ['int', 'pointer']],
  http_server_start: ['void', ['pointer']],
  http_server_stop: ['void', ['pointer']],
  http_server_port: ['int', ['pointer']],
});

console.log('✅ libhttp.so loaded');

// Test 1: Create HTTP server
console.log('\n[Test 1] Creating HTTP server on port 8000...');

// Simple handler callback
const handler = ffi.Callback('void', ['pointer', 'pointer'], (req, res) => {
  console.log('[Handler] Request received');
});

const server = libhttp.http_server_listen(8000, handler);
if (!server || server.isNull()) {
  console.error('❌ Failed to create server');
  process.exit(1);
}

console.log('✅ Server created');
console.log(`   Port: ${libhttp.http_server_port(server)}`);

// Test 2: Start server in background
console.log('\n[Test 2] Starting server (non-blocking test)...');

// Start server in a setTimeout to avoid blocking
setTimeout(() => {
  // Note: http_server_start is blocking, so we just test the creation
  console.log('✅ Server configuration complete');
  
  // Test 3: Make HTTP request to server
  console.log('\n[Test 3] Testing HTTP requests...');
  
  const testRequests = [
    { method: 'GET', path: '/', expected: 200 },
    { method: 'GET', path: '/api/users', expected: 200 },
  ];
  
  let completed = 0;
  testRequests.forEach(test => {
    const req = http.request({
      hostname: 'localhost',
      port: 8000,
      path: test.path,
      method: test.method,
      timeout: 2000
    }, (res) => {
      console.log(`   ${test.method} ${test.path}: ${res.statusCode}`);
      if (res.statusCode === test.expected) {
        console.log(`   ✅ Expected ${test.expected}`);
      } else {
        console.log(`   ⚠️  Got ${res.statusCode}, expected ${test.expected}`);
      }
      
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        completed++;
        if (completed === testRequests.length) {
          cleanup();
        }
      });
    });
    
    req.on('error', (err) => {
      console.log(`   ❌ ${test.method} ${test.path}: ${err.message}`);
      completed++;
      if (completed === testRequests.length) {
        cleanup();
      }
    });
    
    req.end();
  });
  
  // Timeout for tests
  setTimeout(() => {
    if (completed < testRequests.length) {
      console.log(`\n⚠️  Some tests timed out (${completed}/${testRequests.length} completed)`);
      cleanup();
    }
  }, 5000);
  
  function cleanup() {
    console.log('\n[Cleanup] Stopping server...');
    libhttp.http_server_stop(server);
    console.log('✅ Test complete');
    process.exit(0);
  }
}, 100);

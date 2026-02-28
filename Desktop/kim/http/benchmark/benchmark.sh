#!/bin/bash

# Performance Benchmark: C vs Node.js Static File Server
#
# Requirements:
#   - apache2-utils (ab command)
#   - Node.js 14+ (for Express and HTTP servers)
#
# Usage:
#   chmod +x benchmark.sh
#   ./benchmark.sh

set -e

# Configuration
C_PORT=17888
NODEJS_HTTP_PORT=17889
EXPRESS_PORT=17890
ROOT_PATH="../test_files"
AB_REQUESTS=5000
AB_CONCURRENCY=50

RESULTS_FILE="benchmark_results.txt"

echo "================================================"
echo "Static File Server Performance Benchmark"
echo "================================================"
echo ""

# Cleanup
cleanup() {
  pkill -f "static-server" 2>/dev/null || true
  pkill -f "node.*http-server" 2>/dev/null || true
  pkill -f "node.*express-server" 2>/dev/null || true
  sleep 1
}

cleanup

# Create test files if not exist
if [ ! -d "$ROOT_PATH" ]; then
  echo "[SETUP] Creating test files..."
  mkdir -p "$ROOT_PATH"
  echo "<html><body><h1>Test</h1></body></html>" > "$ROOT_PATH/index.html"
  echo '{"message":"Hello World"}' > "$ROOT_PATH/test.json"
  echo "console.log('test');" > "$ROOT_PATH/app.js"
  dd if=/dev/urandom of="$ROOT_PATH/small.dat" bs=1024 count=10 2>/dev/null
  echo "✅ Test files created"
fi

echo ""
echo "================================================"
echo "1. C Static Server"
echo "================================================"
echo ""

# Start C server
echo "[LAUNCH] Starting C server on port $C_PORT..."
../../../dist/stdlib/static-server $C_PORT "$ROOT_PATH" > /tmp/c_server.log 2>&1 &
C_PID=$!
sleep 2

# Health check
if ! curl -s "http://localhost:$C_PORT/static/index.html" > /dev/null; then
  echo "❌ C server failed to start"
  cat /tmp/c_server.log
  exit 1
fi

echo "[BENCHMARK] Running Apache Bench..."
echo "  Requests: $AB_REQUESTS"
echo "  Concurrency: $AB_CONCURRENCY"
echo "  File: small.dat (10 KB)"
echo ""

ab -n $AB_REQUESTS -c $AB_CONCURRENCY -q "http://localhost:$C_PORT/static/small.dat" | tee /tmp/c_results.txt

echo ""
kill $C_PID
sleep 1

echo ""
echo "================================================"
echo "2. Node.js Native HTTP Server"
echo "================================================"
echo ""

# Start Node.js HTTP server
echo "[LAUNCH] Starting Node.js HTTP server on port $NODEJS_HTTP_PORT..."
PORT=$NODEJS_HTTP_PORT ROOT=$ROOT_PATH node http-server.js > /tmp/nodejs_http.log 2>&1 &
NODEJS_PID=$!
sleep 2

# Health check
if ! curl -s "http://localhost:$NODEJS_HTTP_PORT/static/index.html" > /dev/null 2>&1; then
  echo "❌ Node.js HTTP server failed to start"
  cat /tmp/nodejs_http.log
  cleanup
  exit 1
fi

echo "[BENCHMARK] Running Apache Bench..."
echo "  Requests: $AB_REQUESTS"
echo "  Concurrency: $AB_CONCURRENCY"
echo "  File: small.dat (10 KB)"
echo ""

ab -n $AB_REQUESTS -c $AB_CONCURRENCY -q "http://localhost:$NODEJS_HTTP_PORT/static/small.dat" | tee /tmp/nodejs_results.txt

echo ""
kill $NODEJS_PID
sleep 1

echo ""
echo "================================================"
echo "3. Express.js Server"
echo "================================================"
echo ""

# Check if Express is installed
if ! npm ls express > /dev/null 2>&1; then
  echo "⚠️  Express not installed. Installing..."
  npm install express > /dev/null 2>&1
fi

# Start Express server
echo "[LAUNCH] Starting Express server on port $EXPRESS_PORT..."
PORT=$EXPRESS_PORT ROOT=$ROOT_PATH node express-server.js > /tmp/express.log 2>&1 &
EXPRESS_PID=$!
sleep 2

# Health check
if ! curl -s "http://localhost:$EXPRESS_PORT/static/index.html" > /dev/null 2>&1; then
  echo "❌ Express server failed to start"
  cat /tmp/express.log
  cleanup
  exit 1
fi

echo "[BENCHMARK] Running Apache Bench..."
echo "  Requests: $AB_REQUESTS"
echo "  Concurrency: $AB_CONCURRENCY"
echo "  File: small.dat (10 KB)"
echo ""

ab -n $AB_REQUESTS -c $AB_CONCURRENCY -q "http://localhost:$EXPRESS_PORT/static/small.dat" | tee /tmp/express_results.txt

echo ""
kill $EXPRESS_PID
sleep 1

# Cleanup
cleanup

echo ""
echo "================================================"
echo "Performance Summary"
echo "================================================"
echo ""

# Extract RPS from results
echo "Requests per second (RPS):"
echo ""

C_RPS=$(grep "Requests per second" /tmp/c_results.txt | awk '{print $4}')
NODEJS_RPS=$(grep "Requests per second" /tmp/nodejs_results.txt | awk '{print $4}')
EXPRESS_RPS=$(grep "Requests per second" /tmp/express_results.txt | awk '{print $4}')

echo "  C Static Server:        $C_RPS req/s"
echo "  Node.js HTTP Server:    $NODEJS_RPS req/s"
echo "  Express.js Server:      $EXPRESS_RPS req/s"

echo ""
echo "Performance Analysis:"

# Compare C vs Node.js
RATIO=$(echo "scale=2; $C_RPS / $NODEJS_RPS" | bc 2>/dev/null || echo "N/A")
echo "  C is ${RATIO}x faster than Node.js HTTP"

# Compare C vs Express
RATIO2=$(echo "scale=2; $C_RPS / $EXPRESS_RPS" | bc 2>/dev/null || echo "N/A")
echo "  C is ${RATIO2}x faster than Express.js"

echo ""
echo "Detailed results saved in:"
echo "  /tmp/c_results.txt"
echo "  /tmp/nodejs_results.txt"
echo "  /tmp/express_results.txt"
echo ""
echo "✅ Benchmark complete!"

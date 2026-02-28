#!/bin/bash

# Simple Performance Benchmark using curl
# No external dependencies required

set -e

C_PORT=17888
NODEJS_PORT=17889
ROOT_PATH="../test_files"
REQUESTS=1000
CONCURRENCY=10

cleanup() {
  pkill -f "static-server" 2>/dev/null || true
  pkill -f "node.*http-server" 2>/dev/null || true
  sleep 1
}

cleanup

# Create test files
if [ ! -d "$ROOT_PATH" ]; then
  mkdir -p "$ROOT_PATH"
  echo "<html><body><h1>Test</h1></body></html>" > "$ROOT_PATH/index.html"
  echo '{"message":"Hello World"}' > "$ROOT_PATH/test.json"
  echo "console.log('test');" > "$ROOT_PATH/app.js"
  dd if=/dev/urandom of="$ROOT_PATH/small.dat" bs=1024 count=10 2>/dev/null
fi

echo "================================================"
echo "Simple Performance Benchmark (curl-based)"
echo "================================================"
echo ""
echo "Configuration:"
echo "  Requests per thread: $REQUESTS"
echo "  Concurrent threads: $CONCURRENCY"
echo "  File size: 10 KB"
echo ""

# Function to benchmark a server
benchmark_server() {
  local name=$1
  local port=$2
  local url="http://localhost:$port/static/small.dat"

  echo ""
  echo "================================================"
  echo "Testing: $name"
  echo "================================================"
  echo ""

  # Warmup
  echo "[WARMUP] Sending 10 warmup requests..."
  for i in {1..10}; do
    curl -s "$url" > /dev/null 2>&1
  done

  echo "✅ Warmup complete"
  echo ""
  echo "[BENCHMARK] Running $REQUESTS requests with $CONCURRENCY concurrency..."

  local start=$(date +%s%N)
  local total_bytes=0
  local errors=0

  # Parallel requests using background jobs
  for i in $(seq 1 $REQUESTS); do
    (
      response=$(curl -s -w "%{http_code}|%{size_download}" "$url" 2>/dev/null)
      status=${response##*|}
      bytes=${response##*|}
      if [ "$status" = "200" ]; then
        echo "$bytes"
      else
        echo "ERROR"
      fi
    ) &

    # Limit concurrency
    if [ $((i % CONCURRENCY)) -eq 0 ]; then
      wait
    fi
  done

  wait

  local end=$(date +%s%N)
  local duration_ns=$((end - start))
  local duration_ms=$((duration_ns / 1000000))
  local duration_sec=$(echo "scale=2; $duration_ms / 1000" | bc)

  # Calculate stats
  local rps=$(echo "scale=2; $REQUESTS / ($duration_ms / 1000)" | bc)
  local avg_time=$(echo "scale=2; $duration_ms / $REQUESTS" | bc)

  echo ""
  echo "Results for $name:"
  echo "  Duration: ${duration_sec}s"
  echo "  Requests: $REQUESTS"
  echo "  RPS: $rps req/s"
  echo "  Avg latency: ${avg_time}ms"
}

# Test C Server
echo "[1/2] Starting C Static Server on port $C_PORT..."
../../../dist/stdlib/static-server $C_PORT "$ROOT_PATH" > /tmp/c_bench.log 2>&1 &
C_PID=$!
sleep 2

if curl -s "http://localhost:$C_PORT/static/index.html" > /dev/null; then
  benchmark_server "C Static Server" $C_PORT
  C_RPS=$(curl -s "http://localhost:$C_PORT/health" 2>/dev/null | grep -o 'ok' || echo "N/A")
else
  echo "❌ C server failed to start"
fi

kill $C_PID 2>/dev/null
sleep 1

# Test Node.js Server
echo ""
echo "[2/2] Starting Node.js HTTP Server on port $NODEJS_PORT..."
PORT=$NODEJS_PORT ROOT=$ROOT_PATH timeout 120 node http-server.js > /tmp/nodejs_bench.log 2>&1 &
NODEJS_PID=$!
sleep 2

if curl -s "http://localhost:$NODEJS_PORT/static/index.html" > /dev/null 2>&1; then
  benchmark_server "Node.js HTTP Server" $NODEJS_PORT
else
  echo "❌ Node.js server failed to start"
  cat /tmp/nodejs_bench.log
fi

kill $NODEJS_PID 2>/dev/null
sleep 1

cleanup

echo ""
echo "================================================"
echo "✅ Benchmark complete!"
echo "================================================"

#!/bin/bash

# Concurrent Performance Benchmark

C_PORT=18888
NODEJS_PORT=18889
ROOT_PATH="../test_files"

cleanup() {
  pkill -f "static-server" 2>/dev/null || true
  pkill -f "node.*http-server" 2>/dev/null || true
  sleep 1
}

# Create test files
if [ ! -d "$ROOT_PATH" ]; then
  mkdir -p "$ROOT_PATH"
  echo "<html><body><h1>Test</h1></body></html>" > "$ROOT_PATH/index.html"
  echo '{"message":"Hello World"}' > "$ROOT_PATH/test.json"
  echo "console.log('test');" > "$ROOT_PATH/app.js"
  dd if=/dev/urandom of="$ROOT_PATH/small.dat" bs=1024 count=10 2>/dev/null
fi

cleanup

echo "================================================"
echo "Concurrent Performance Benchmark"
echo "================================================"
echo ""
echo "Configuration:"
echo "  Total requests: 500"
echo "  Concurrent workers: 10"
echo "  File size: 10 KB"
echo ""

# Function to run concurrent benchmark
concurrent_bench() {
  local name=$1
  local port=$2
  local url="http://localhost:$port/static/small.dat"
  local total_requests=500
  local concurrent_workers=10

  echo "[Test] $name"
  echo "=========================================="
  echo ""

  local start=$(date +%s%N)
  local success=0
  local failed=0

  # Run concurrent requests
  for i in $(seq 1 $total_requests); do
    (
      if curl -s --connect-timeout 5 --max-time 10 "$url" > /dev/null 2>&1; then
        echo "S"
      else
        echo "F"
      fi
    ) &

    # Limit concurrency
    if [ $((i % concurrent_workers)) -eq 0 ]; then
      # Wait for batch to complete
      wait

      # Show progress
      if [ $((i % 50)) -eq 0 ]; then
        echo "  Progress: $i/$total_requests"
      fi
    fi
  done

  # Wait for remaining jobs
  wait

  local end=$(date +%s%N)
  local duration_ns=$((end - start))
  local duration_ms=$((duration_ns / 1000000))
  local duration_sec=$(echo "scale=3; $duration_ms / 1000" | bc)

  local rps=$(echo "scale=1; $total_requests * 1000 / $duration_ms" | bc)
  local avg_latency=$(echo "scale=2; $duration_ms / $total_requests" | bc)

  echo ""
  echo "Results for $name:"
  echo "  Duration: ${duration_sec}s"
  echo "  Requests: $total_requests"
  echo "  RPS: $rps req/s"
  echo "  Avg latency: ${avg_latency}ms"
  echo ""

  echo "$rps"
}

# Test C Server
../../../dist/stdlib/static-server $C_PORT "$ROOT_PATH" > /tmp/c_bench.log 2>&1 &
C_PID=$!
sleep 2

if curl -s "http://localhost:$C_PORT/static/small.dat" > /dev/null 2>&1; then
  C_RPS=$(concurrent_bench "C Static Server" $C_PORT)
else
  echo "❌ C server failed"
  C_RPS="0"
fi

kill $C_PID 2>/dev/null
sleep 2

# Test Node.js Server
PORT=$NODEJS_PORT ROOT=$ROOT_PATH timeout 120 node http-server.js > /tmp/nodejs_bench.log 2>&1 &
NODEJS_PID=$!
sleep 2

if curl -s "http://localhost:$NODEJS_PORT/static/small.dat" > /dev/null 2>&1; then
  NODEJS_RPS=$(concurrent_bench "Node.js HTTP Server" $NODEJS_PORT)
else
  echo "❌ Node.js server failed"
  NODEJS_RPS="0"
fi

kill $NODEJS_PID 2>/dev/null
sleep 1

cleanup

echo ""
echo "================================================"
echo "Performance Comparison (Concurrent)"
echo "================================================"
echo ""
echo "C Static Server:       $C_RPS req/s"
echo "Node.js HTTP Server:   $NODEJS_RPS req/s"

if [ "$NODEJS_RPS" != "0" ]; then
  RATIO=$(echo "scale=2; $C_RPS / $NODEJS_RPS" | bc)
  echo ""
  echo "⚡ C is ${RATIO}x faster than Node.js in concurrent workloads"
fi

echo ""
echo "✅ Benchmark complete!"

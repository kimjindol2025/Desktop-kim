#!/bin/bash

# Large File Performance Benchmark (1MB)

C_PORT=18888
NODEJS_PORT=18889
ROOT_PATH="../test_files"

cleanup() {
  pkill -f "static-server" 2>/dev/null || true
  pkill -f "node.*http-server" 2>/dev/null || true
  sleep 1
}

# Ensure large.dat exists
if [ ! -f "$ROOT_PATH/large.dat" ]; then
  echo "Creating 1MB test file..."
  dd if=/dev/urandom of="$ROOT_PATH/large.dat" bs=1024 count=1024 2>/dev/null
fi

cleanup

echo "================================================"
echo "Large File Benchmark (1MB)"
echo "================================================"
echo ""
echo "Configuration:"
echo "  Total requests: 100"
echo "  Concurrent workers: 5"
echo "  File size: 1 MB"
echo ""

# Function to run concurrent benchmark
concurrent_bench() {
  local name=$1
  local port=$2
  local url="http://localhost:$port/static/large.dat"
  local total_requests=100
  local concurrent_workers=5

  echo "[Test] $name"
  echo "=========================================="
  echo ""

  local start=$(date +%s%N)
  local success=0
  local failed=0

  # Run concurrent requests
  for i in $(seq 1 $total_requests); do
    (
      if curl -s --connect-timeout 10 --max-time 30 "$url" > /dev/null 2>&1; then
        echo "S"
      else
        echo "F"
      fi
    ) &

    # Limit concurrency
    if [ $((i % concurrent_workers)) -eq 0 ]; then
      wait
      if [ $((i % 20)) -eq 0 ]; then
        echo "  Progress: $i/$total_requests"
      fi
    fi
  done

  wait

  local end=$(date +%s%N)
  local duration_ns=$((end - start))
  local duration_ms=$((duration_ns / 1000000))
  local duration_sec=$(echo "scale=3; $duration_ms / 1000" | bc)

  local rps=$(echo "scale=2; $total_requests * 1000 / $duration_ms" | bc)
  local avg_latency=$(echo "scale=2; $duration_ms / $total_requests" | bc)
  local throughput=$(echo "scale=1; ($total_requests * 1024) / ($duration_ms / 1000)" | bc)

  echo ""
  echo "Results for $name:"
  echo "  Duration: ${duration_sec}s"
  echo "  Requests: $total_requests"
  echo "  RPS: $rps req/s"
  echo "  Avg latency: ${avg_latency}ms"
  echo "  Throughput: ${throughput} MB/s"
  echo ""

  echo "$rps|$throughput"
}

# Test C Server
echo "Starting C Static Server on port $C_PORT..."
../../../dist/stdlib/static-server $C_PORT "$ROOT_PATH" > /tmp/c_bench_large.log 2>&1 &
C_PID=$!
sleep 2

if curl -s "http://localhost:$C_PORT/static/large.dat" > /dev/null 2>&1; then
  C_RESULT=$(concurrent_bench "C Static Server" $C_PORT)
  C_RPS=$(echo "$C_RESULT" | cut -d'|' -f1)
  C_THROUGHPUT=$(echo "$C_RESULT" | cut -d'|' -f2)
else
  echo "❌ C server failed"
  C_RPS="0"
  C_THROUGHPUT="0"
fi

kill $C_PID 2>/dev/null
sleep 2

# Test Node.js Server
echo "Starting Node.js HTTP Server on port $NODEJS_PORT..."
PORT=$NODEJS_PORT ROOT=$ROOT_PATH timeout 300 node http-server.js > /tmp/nodejs_bench_large.log 2>&1 &
NODEJS_PID=$!
sleep 2

if curl -s "http://localhost:$NODEJS_PORT/static/large.dat" > /dev/null 2>&1; then
  NODEJS_RESULT=$(concurrent_bench "Node.js HTTP Server" $NODEJS_PORT)
  NODEJS_RPS=$(echo "$NODEJS_RESULT" | cut -d'|' -f1)
  NODEJS_THROUGHPUT=$(echo "$NODEJS_RESULT" | cut -d'|' -f2)
else
  echo "❌ Node.js server failed"
  NODEJS_RPS="0"
  NODEJS_THROUGHPUT="0"
fi

kill $NODEJS_PID 2>/dev/null
sleep 1

cleanup

echo "================================================"
echo "Performance Comparison (1MB File)"
echo "================================================"
echo ""
echo "Requests per Second (RPS):"
echo "  C Static Server:       $C_RPS req/s"
echo "  Node.js HTTP Server:   $NODEJS_RPS req/s"
echo ""
echo "Throughput (MB/s):"
echo "  C Static Server:       $C_THROUGHPUT MB/s"
echo "  Node.js HTTP Server:   $NODEJS_THROUGHPUT MB/s"

if [ "$NODEJS_RPS" != "0" ]; then
  # Use bc with explicit scale
  RATIO=$(echo "scale=2; $C_RPS / $NODEJS_RPS" | bc 2>/dev/null || echo "N/A")
  THROUGHPUT_RATIO=$(echo "scale=2; $C_THROUGHPUT / $NODEJS_THROUGHPUT" | bc 2>/dev/null || echo "N/A")
  echo ""
  echo "📊 Performance Analysis:"
  echo "  RPS Ratio: C is ${RATIO}x faster"
  echo "  Throughput Ratio: C is ${THROUGHPUT_RATIO}x faster"
fi

echo ""
echo "✅ Benchmark complete!"

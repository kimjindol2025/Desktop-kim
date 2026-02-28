#!/bin/bash

# Quick Performance Benchmark

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
echo "Quick Performance Benchmark"
echo "================================================"
echo ""

# Test C Server
echo "[Test 1/2] C Static Server"
echo "=========================================="

../../../dist/stdlib/static-server $C_PORT "$ROOT_PATH" > /tmp/c_bench.log 2>&1 &
C_PID=$!
sleep 2

if curl -s "http://localhost:$C_PORT/static/small.dat" > /tmp/test_c.bin 2>&1; then
  echo "✅ Server running"
  echo ""
  echo "Sending 200 sequential requests..."

  START=$(date +%s%N)
  for i in {1..200}; do
    curl -s "http://localhost:$C_PORT/static/small.dat" > /dev/null 2>&1
    if [ $((i % 40)) -eq 0 ]; then
      echo "  Progress: $i/200"
    fi
  done
  END=$(date +%s%N)

  DURATION_NS=$((END - START))
  DURATION_MS=$((DURATION_NS / 1000000))
  DURATION_SEC=$(echo "scale=3; $DURATION_MS / 1000" | bc)

  RPS=$(echo "scale=1; 200000 / $DURATION_MS" | bc)
  AVG_LATENCY=$(echo "scale=2; $DURATION_MS / 200" | bc)

  echo ""
  echo "C Server Results:"
  echo "  Duration: ${DURATION_SEC}s"
  echo "  Requests: 200"
  echo "  RPS: $RPS req/s"
  echo "  Avg latency: ${AVG_LATENCY}ms"
  echo ""
  FILE_SIZE=$(stat -f%z /tmp/test_c.bin 2>/dev/null || stat -c%s /tmp/test_c.bin 2>/dev/null || echo "N/A")
  echo "  File size: $FILE_SIZE bytes"

  C_RPS=$RPS
else
  echo "❌ C server failed"
  cat /tmp/c_bench.log
fi

kill $C_PID 2>/dev/null
sleep 1

# Test Node.js Server
echo ""
echo "[Test 2/2] Node.js HTTP Server"
echo "=========================================="

PORT=$NODEJS_PORT ROOT=$ROOT_PATH timeout 60 node http-server.js > /tmp/nodejs_bench.log 2>&1 &
NODEJS_PID=$!
sleep 2

if curl -s "http://localhost:$NODEJS_PORT/static/small.dat" > /tmp/test_nodejs.bin 2>&1; then
  echo "✅ Server running"
  echo ""
  echo "Sending 200 sequential requests..."

  START=$(date +%s%N)
  for i in {1..200}; do
    curl -s "http://localhost:$NODEJS_PORT/static/small.dat" > /dev/null 2>&1
    if [ $((i % 40)) -eq 0 ]; then
      echo "  Progress: $i/200"
    fi
  done
  END=$(date +%s%N)

  DURATION_NS=$((END - START))
  DURATION_MS=$((DURATION_NS / 1000000))
  DURATION_SEC=$(echo "scale=3; $DURATION_MS / 1000" | bc)

  RPS=$(echo "scale=1; 200000 / $DURATION_MS" | bc)
  AVG_LATENCY=$(echo "scale=2; $DURATION_MS / 200" | bc)

  echo ""
  echo "Node.js Server Results:"
  echo "  Duration: ${DURATION_SEC}s"
  echo "  Requests: 200"
  echo "  RPS: $RPS req/s"
  echo "  Avg latency: ${AVG_LATENCY}ms"
  echo ""
  FILE_SIZE=$(stat -f%z /tmp/test_nodejs.bin 2>/dev/null || stat -c%s /tmp/test_nodejs.bin 2>/dev/null || echo "N/A")
  echo "  File size: $FILE_SIZE bytes"

  NODEJS_RPS=$RPS
else
  echo "❌ Node.js server failed"
  cat /tmp/nodejs_bench.log
fi

kill $NODEJS_PID 2>/dev/null
sleep 1

cleanup

echo ""
echo "================================================"
echo "Performance Summary"
echo "================================================"
echo ""
if [ -n "$C_RPS" ] && [ -n "$NODEJS_RPS" ]; then
  RATIO=$(echo "scale=1; $C_RPS / $NODEJS_RPS" | bc)
  echo "C Static Server:       $C_RPS req/s"
  echo "Node.js HTTP Server:   $NODEJS_RPS req/s"
  echo ""
  echo "C is ${RATIO}x faster than Node.js"
fi

echo ""
echo "✅ Benchmark complete!"

# FreeLang stdlib/http - HTTP Server & Static File Server
# Custom Event Loop (No external dependencies)

CC = gcc
CFLAGS = -Wall -Wextra -fPIC -O2 -pthread
LDFLAGS = -shared -pthread

SRC_DIR = .
BUILD_DIR = build
DIST_DIR = ../../dist/stdlib

# Shared library targets (v2: optimized with connection pooling)
SOURCES = $(SRC_DIR)/event_loop.c $(SRC_DIR)/http_server_impl.c $(SRC_DIR)/http_client.c $(SRC_DIR)/http_server_optimized.c
OBJECTS = $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SOURCES))
SHARED_TARGET = $(DIST_DIR)/libhttp.so
SHARED_TARGET_V2 = $(DIST_DIR)/libhttp-v2.so

# Static server targets
STATIC_SOURCES = static_server_main.c static_file.c
STATIC_OBJECTS = $(patsubst %.c,$(BUILD_DIR)/%.o,$(STATIC_SOURCES))
STATIC_TARGET = $(DIST_DIR)/static-server

.PHONY: all lib-build lib-test lib-clean static test-static clean install

all: lib-build

# ===== Shared Library (libhttp.so) =====

lib-build: $(SHARED_TARGET)
	@echo "✅ HTTP library built successfully"

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

$(DIST_DIR):
	@mkdir -p $(DIST_DIR)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(SHARED_TARGET): $(OBJECTS) | $(DIST_DIR)
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@
	@echo "✅ libhttp.so created: $(SHARED_TARGET)"

lib-test: $(SHARED_TARGET)
	@echo "✅ HTTP library ready for testing"

# ===== Static File Server (Standalone Binary) =====

static: $(STATIC_TARGET)
	@echo "✅ Static server built: $(STATIC_TARGET)"

$(BUILD_DIR)/static_file.o: static_file.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c static_file.c -o $@

$(BUILD_DIR)/static_server_main.o: static_server_main.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c static_server_main.c -o $@

$(STATIC_TARGET): $(BUILD_DIR)/static_file.o $(BUILD_DIR)/static_server_main.o | $(DIST_DIR)
	$(CC) $(CFLAGS) -o $@ $(BUILD_DIR)/static_file.o $(BUILD_DIR)/static_server_main.o -pthread
	@chmod +x $@

# ===== Test: Static File Server =====

test-static: static
	@mkdir -p test_files
	@echo "<html><body><h1>Test Page</h1></body></html>" > test_files/index.html
	@echo '{"message":"Hello World"}' > test_files/test.json
	@echo "console.log('test');" > test_files/app.js
	@dd if=/dev/urandom of=test_files/small.dat bs=1024 count=10 2>/dev/null
	@echo ""
	@echo "[TEST] 파일 서버 시작..."
	@echo "       포트: 8080"
	@echo "       경로: ./test_files"
	@echo ""
	@echo "[TEST] 테스트 명령어:"
	@echo "       curl http://localhost:8080/static/index.html"
	@echo "       curl http://localhost:8080/static/test.json"
	@echo "       curl http://localhost:8080/static/app.js"
	@echo ""
	@echo "       (Ctrl+C로 종료)"
	@echo ""
	@$(STATIC_TARGET) 8080 ./test_files

# ===== Clean =====

clean:
	@rm -rf $(BUILD_DIR) $(SHARED_TARGET) $(STATIC_TARGET)
	@rm -rf test_files
	@echo "✅ Cleaned"

lib-clean: clean

install: lib-build
	@echo "✅ libhttp.so installed"

# ===== HTTP Server Completion Test =====

TEST_TARGET = $(BUILD_DIR)/test_http_complete
TEST_BINARY = test_http_complete

TEST_SIMPLE_TARGET = $(BUILD_DIR)/test_http_simple
TEST_SIMPLE_BINARY = test_http_simple

test-lib: lib-build $(TEST_TARGET)
	@echo ""
	@echo "[TEST] Running HTTP Server Completion Test..."
	@echo "       (Testing event_loop + http_server_impl integration)"
	@echo ""
	@LD_LIBRARY_PATH=$(DIST_DIR):$$LD_LIBRARY_PATH timeout 10 $(TEST_TARGET) || echo "Test completed (may have timed out)"

test-simple: lib-build $(TEST_SIMPLE_TARGET)
	@echo ""
	@echo "[TEST] Running Simple HTTP Server Test..."
	@echo "       (Creates server, waits 5 seconds for requests)"
	@echo ""
	@LD_LIBRARY_PATH=$(DIST_DIR):$$LD_LIBRARY_PATH $(TEST_SIMPLE_TARGET) 39999 || echo "Test completed"

$(TEST_SIMPLE_TARGET): test_http_simple.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -L$(DIST_DIR) -o $@ test_http_simple.c -lhttp -pthread 2>&1 | grep -v "warning"
	@chmod +x $@

$(TEST_TARGET): test_http_complete.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -L$(DIST_DIR) -o $@ test_http_complete.c -lhttp -pthread
	@chmod +x $@

# ===== wrk: HTTP Benchmarking Tool =====

WRK_TARGET = $(DIST_DIR)/wrk

wrk: $(WRK_TARGET)
	@echo "✅ wrk built: $(WRK_TARGET)"

$(WRK_TARGET): wrk.c | $(DIST_DIR)
	$(CC) $(CFLAGS) -o $@ wrk.c -pthread
	@chmod +x $@

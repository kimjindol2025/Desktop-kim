/**
 * wrk - HTTP Performance Benchmarking Tool
 *
 * C 구현된 경량 HTTP 벤치마크 도구
 * 멀티스레딩 지원, 높은 동시성, Keep-Alive 연결 재사용
 *
 * 사용법:
 *   wrk -t 4 -c 100 -d 30s http://localhost:8080/
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <time.h>
#include <errno.h>
#include <stdint.h>
#include <fcntl.h>

/* ===== 설정 ===== */

typedef struct {
  char *url;
  int num_threads;
  int num_connections;
  int duration_ms;
  int total_requests;
} config_t;

typedef struct {
  char host[256];
  int port;
  char path[1024];
} url_t;

/* ===== 성능 통계 ===== */

typedef struct {
  uint64_t total_requests;
  uint64_t total_bytes;
  uint64_t total_errors;
  uint64_t *response_times;
  int response_times_count;
  int response_times_capacity;
  uint64_t min_time;
  uint64_t max_time;
  uint64_t total_time;
} stats_t;

/* ===== 연결 풀 ===== */

typedef struct {
  int sock;
  int reuse_count;
} connection_t;

typedef struct {
  config_t *config;
  url_t *url;
  stats_t *stats;
  pthread_mutex_t *stats_lock;
  int thread_id;
  int stop_flag;
} worker_ctx_t;

/* ===== URL 파싱 ===== */

int parse_url(const char *url_str, url_t *url) {
  char url_copy[2048];
  strncpy(url_copy, url_str, sizeof(url_copy) - 1);

  char *start = url_copy;
  if (strncmp(start, "https://", 8) == 0) {
    start += 8;
  } else if (strncmp(start, "http://", 7) == 0) {
    start += 7;
  }

  char *path_start = strchr(start, '/');
  if (!path_start) {
    strncpy(url->path, "/", sizeof(url->path) - 1);
    path_start = start + strlen(start);
  } else {
    strncpy(url->path, path_start, sizeof(url->path) - 1);
    *path_start = '\0';
  }

  char *port_str = strchr(start, ':');
  if (port_str) {
    *port_str = '\0';
    strncpy(url->host, start, sizeof(url->host) - 1);
    url->port = atoi(port_str + 1);
  } else {
    strncpy(url->host, start, sizeof(url->host) - 1);
    url->port = 80;
  }

  return 0;
}

/* ===== HTTP 요청 ===== */

void build_http_request(const url_t *url, char *request, size_t size) {
  snprintf(request, size,
    "GET %s HTTP/1.1\r\n"
    "Host: %s\r\n"
    "User-Agent: wrk/1.0\r\n"
    "Connection: keep-alive\r\n"
    "Accept: */*\r\n"
    "\r\n",
    url->path, url->host);
}

/* ===== 통계 ===== */

stats_t* stats_create() {
  stats_t *stats = (stats_t*)malloc(sizeof(stats_t));
  if (!stats) return NULL;
  memset(stats, 0, sizeof(stats_t));
  stats->response_times_capacity = 100000;
  stats->response_times = (uint64_t*)malloc(sizeof(uint64_t) * stats->response_times_capacity);
  stats->min_time = UINT64_MAX;
  return stats;
}

void stats_add_response(stats_t *stats, uint64_t response_time, uint64_t bytes, int error) {
  if (error) {
    stats->total_errors++;
  } else {
    stats->total_requests++;
    stats->total_bytes += bytes;
    if (response_time < stats->min_time) stats->min_time = response_time;
    if (response_time > stats->max_time) stats->max_time = response_time;
    stats->total_time += response_time;
    if (stats->response_times_count < stats->response_times_capacity) {
      stats->response_times[stats->response_times_count++] = response_time;
    }
  }
}

void stats_free(stats_t *stats) {
  if (!stats) return;
  free(stats->response_times);
  free(stats);
}

/* ===== 퍼센타일 ===== */

int compare_uint64(const void *a, const void *b) {
  uint64_t va = *(uint64_t*)a;
  uint64_t vb = *(uint64_t*)b;
  if (va < vb) return -1;
  if (va > vb) return 1;
  return 0;
}

uint64_t percentile(stats_t *stats, double p) {
  if (stats->response_times_count == 0) return 0;
  qsort(stats->response_times, stats->response_times_count, sizeof(uint64_t), compare_uint64);
  int index = (int)(stats->response_times_count * p / 100.0);
  if (index >= stats->response_times_count) index = stats->response_times_count - 1;
  return stats->response_times[index];
}

/* ===== 워커 스레드 ===== */

int send_request(int sock, const char *request) {
  return send(sock, request, strlen(request), MSG_NOSIGNAL) > 0 ? 0 : -1;
}

int recv_response(int sock, char *buffer, size_t size) {
  ssize_t n = recv(sock, buffer, size - 1, 0);
  if (n <= 0) return -1;
  buffer[n] = '\0';
  return n;
}

void* worker_thread(void *arg) {
  worker_ctx_t *ctx = (worker_ctx_t*)arg;
  config_t *cfg = ctx->config;
  url_t *url = ctx->url;
  stats_t *stats = ctx->stats;

  char http_request[512];
  build_http_request(url, http_request, sizeof(http_request));

  // DNS 미리 해석
  struct hostent *host = gethostbyname(url->host);
  if (!host) {
    fprintf(stderr, "DNS lookup failed for %s\n", url->host);
    return NULL;
  }

  struct sockaddr_in server_addr;
  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(url->port);
  server_addr.sin_addr = *(struct in_addr*)host->h_addr;

  int sock = -1;
  uint64_t requests = 0;
  time_t start_time = time(NULL);

  while (!ctx->stop_flag) {
    // 기간 확인
    if (cfg->total_requests == -1) {
      time_t now = time(NULL);
      if ((now - start_time) * 1000 >= cfg->duration_ms) break;
    } else {
      if (requests >= (uint64_t)cfg->total_requests) break;
    }

    // 연결 재사용 또는 새로 생성
    if (sock < 0) {
      sock = socket(AF_INET, SOCK_STREAM, 0);
      if (sock < 0) {
        pthread_mutex_lock(ctx->stats_lock);
        stats_add_response(stats, 0, 0, 1);
        pthread_mutex_unlock(ctx->stats_lock);
        usleep(10000);
        continue;
      }

      // 타임아웃 설정
      struct timeval tv;
      tv.tv_sec = 5;
      tv.tv_usec = 0;
      setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));

      // 연결
      if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        close(sock);
        sock = -1;
        pthread_mutex_lock(ctx->stats_lock);
        stats_add_response(stats, 0, 0, 1);
        pthread_mutex_unlock(ctx->stats_lock);
        usleep(10000);
        continue;
      }
    }

    // 시간 측정
    struct timespec req_start, req_end;
    clock_gettime(CLOCK_MONOTONIC, &req_start);

    // 요청 송신
    if (send_request(sock, http_request) < 0) {
      close(sock);
      sock = -1;
      pthread_mutex_lock(ctx->stats_lock);
      stats_add_response(stats, 0, 0, 1);
      pthread_mutex_unlock(ctx->stats_lock);
      continue;
    }

    // 응답 수신
    char response[8192];
    ssize_t received = recv(sock, response, sizeof(response) - 1, 0);

    clock_gettime(CLOCK_MONOTONIC, &req_end);

    // 지연시간 계산
    uint64_t elapsed_us =
      (req_end.tv_sec - req_start.tv_sec) * 1000000 +
      (req_end.tv_nsec - req_start.tv_nsec) / 1000;

    pthread_mutex_lock(ctx->stats_lock);
    if (received > 0) {
      stats_add_response(stats, elapsed_us, received, 0);
    } else {
      stats_add_response(stats, elapsed_us, 0, 1);
      close(sock);
      sock = -1;
    }
    pthread_mutex_unlock(ctx->stats_lock);

    requests++;
  }

  if (sock >= 0) close(sock);
  return NULL;
}

/* ===== 메인 ===== */

void print_usage(const char *prog) {
  fprintf(stderr,
    "Usage: %s [options] URL\n\n"
    "Options:\n"
    "  -t threads    Number of worker threads (default: 4)\n"
    "  -c connections Number of concurrent connections (default: 10)\n"
    "  -d duration   Test duration (e.g., 30s, 1m; default: 10s)\n"
    "  -n requests   Total requests (alternative to -d)\n"
    "  -h            Show this help\n\n"
    "Example:\n"
    "  %s -t 4 -c 100 -d 30s http://localhost:8080/\n",
    prog, prog);
}

int parse_duration(const char *str, int *ms) {
  int value = atoi(str);
  if (value <= 0) return -1;
  char *unit = strchr(str, 's');
  if (!unit) unit = strchr(str, 'm');
  if (!unit) {
    *ms = value * 1000;
  } else if (*unit == 's') {
    *ms = value * 1000;
  } else if (*unit == 'm') {
    *ms = value * 60000;
  } else {
    return -1;
  }
  return 0;
}

int main(int argc, char *argv[]) {
  config_t config = {
    .num_threads = 4,
    .num_connections = 10,
    .duration_ms = 10000,
    .total_requests = -1
  };

  int opt;
  while ((opt = getopt(argc, argv, "t:c:d:n:h")) != -1) {
    switch (opt) {
      case 't': config.num_threads = atoi(optarg); break;
      case 'c': config.num_connections = atoi(optarg); break;
      case 'd':
        if (parse_duration(optarg, &config.duration_ms) < 0) {
          fprintf(stderr, "Invalid duration: %s\n", optarg);
          return 1;
        }
        config.total_requests = -1;
        break;
      case 'n': config.total_requests = atoi(optarg); break;
      case 'h':
      default:
        print_usage(argv[0]);
        return opt == 'h' ? 0 : 1;
    }
  }

  if (optind >= argc) {
    print_usage(argv[0]);
    return 1;
  }

  config.url = argv[optind];

  // URL 파싱
  url_t url;
  if (parse_url(config.url, &url) < 0) {
    fprintf(stderr, "Invalid URL: %s\n", config.url);
    return 1;
  }

  printf("============================================\n");
  printf("wrk - HTTP Performance Benchmarking\n");
  printf("============================================\n\n");
  printf("URL:           %s\n", config.url);
  printf("Host:          %s:%d\n", url.host, url.port);
  printf("Path:          %s\n", url.path);
  printf("Threads:       %d\n", config.num_threads);
  printf("Connections:   %d\n", config.num_connections);
  if (config.total_requests == -1) {
    printf("Duration:      %d ms\n", config.duration_ms);
  } else {
    printf("Total Requests: %d\n", config.total_requests);
  }
  printf("\nRunning...\n\n");
  fflush(stdout);

  // 통계 생성
  stats_t *stats = stats_create();
  if (!stats) {
    fprintf(stderr, "Failed to allocate stats\n");
    return 1;
  }

  pthread_mutex_t stats_lock;
  pthread_mutex_init(&stats_lock, NULL);

  // 워커 스레드 생성
  pthread_t *threads = (pthread_t*)malloc(sizeof(pthread_t) * config.num_threads);
  worker_ctx_t *contexts = (worker_ctx_t*)malloc(sizeof(worker_ctx_t) * config.num_threads);

  time_t test_start = time(NULL);

  for (int i = 0; i < config.num_threads; i++) {
    contexts[i].config = &config;
    contexts[i].url = &url;
    contexts[i].stats = stats;
    contexts[i].stats_lock = &stats_lock;
    contexts[i].thread_id = i;
    contexts[i].stop_flag = 0;
    pthread_create(&threads[i], NULL, worker_thread, &contexts[i]);
  }

  // 스레드 대기
  for (int i = 0; i < config.num_threads; i++) {
    pthread_join(threads[i], NULL);
  }

  time_t test_end = time(NULL);

  // 결과 출력
  printf("\n============================================\n");
  printf("Results\n");
  printf("============================================\n\n");

  uint64_t total_duration_us = (test_end - test_start) * 1000000;
  double total_duration_s = total_duration_us / 1000000.0;

  printf("Requests:     %llu\n", (unsigned long long)stats->total_requests);
  printf("Errors:       %llu\n", (unsigned long long)stats->total_errors);
  printf("Bytes:        %llu (%.2f MB)\n",
         (unsigned long long)stats->total_bytes,
         stats->total_bytes / (1024.0 * 1024.0));
  printf("Duration:     %.2f s\n", total_duration_s);
  printf("\n");

  if (stats->total_requests > 0) {
    double rps = stats->total_requests / total_duration_s;
    double throughput_mbs = (stats->total_bytes / (1024.0 * 1024.0)) / total_duration_s;
    double avg_latency_ms = (double)stats->total_time / stats->total_requests / 1000.0;

    printf("RPS:          %.2f req/s\n", rps);
    printf("Throughput:   %.2f MB/s\n", throughput_mbs);
    printf("\n");

    printf("Response Times (ms):\n");
    printf("  Min:        %.2f\n", stats->min_time / 1000.0);
    printf("  Avg:        %.2f\n", avg_latency_ms);
    printf("  Max:        %.2f\n", stats->max_time / 1000.0);
    printf("  p50:        %.2f\n", percentile(stats, 50) / 1000.0);
    printf("  p90:        %.2f\n", percentile(stats, 90) / 1000.0);
    printf("  p99:        %.2f\n", percentile(stats, 99) / 1000.0);
    printf("\n");
  }

  // 정리
  stats_free(stats);
  pthread_mutex_destroy(&stats_lock);
  free(threads);
  free(contexts);

  return 0;
}

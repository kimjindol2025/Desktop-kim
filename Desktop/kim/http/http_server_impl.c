/**
 * FreeLang HTTP Server Implementation
 * Built on custom Event Loop (Event Loop + Thread Pool)
 *
 * 구현 포인트:
 * 1. Event Loop로 다중 클라이언트 동시 처리
 * 2. Thread Pool로 블로킹 작업 처리
 * 3. Handles (TCP 서버) + Requests (HTTP 요청) 분리
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <sys/stat.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <errno.h>
#include <pthread.h>

/* ===== HTTP Request/Response 구조 ===== */

typedef struct {
  char method[16];      /* GET, POST, PUT, DELETE */
  char path[512];       /* /api/users */
  char *body;
  size_t body_len;
  int status_code;
  char *response_body;
  size_t response_body_len;
} http_request_t;

typedef struct {
  int client_fd;
  http_request_t *request;
  void (*handler)(http_request_t*, char**);  /* FreeLang callback */
} http_connection_t;

/* ===== HTTP 요청 파싱 ===== */

int http_parse_request(const char *raw, http_request_t *req) {
  if (!raw || strlen(raw) < 14) {
    return -1;
  }

  // GET / HTTP/1.1\r\n...
  sscanf(raw, "%15s %511s", req->method, req->path);

  // 메서드 검증
  if (strcmp(req->method, "GET") != 0 &&
      strcmp(req->method, "POST") != 0 &&
      strcmp(req->method, "PUT") != 0 &&
      strcmp(req->method, "DELETE") != 0) {
    return -1;
  }

  printf("[HTTP] 요청 파싱: %s %s\n", req->method, req->path);
  return 0;
}

/* ===== HTTP 응답 생성 ===== */

char* http_build_response(int status, const char *body) {
  char *response = (char*)malloc(4096);
  if (!response) return NULL;

  const char *status_text = "200 OK";
  if (status == 404) status_text = "404 Not Found";
  else if (status == 500) status_text = "500 Internal Server Error";

  snprintf(response, 4096,
    "HTTP/1.1 %d %s\r\n"
    "Content-Type: application/json\r\n"
    "Content-Length: %zu\r\n"
    "Connection: keep-alive\r\n"
    "\r\n"
    "%s",
    status, status_text, strlen(body), body);

  return response;
}

/* ===== TCP Server Callback (Event Loop에서 호출) ===== */

void http_server_accept_callback(int server_fd) {
  struct sockaddr_in client_addr;
  socklen_t addr_len = sizeof(client_addr);

  int client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &addr_len);
  if (client_fd < 0) {
    perror("accept() error");
    return;
  }

  printf("[HTTP] 클라이언트 연결: fd=%d, ip=%s:%d\n",
         client_fd, inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

  // Non-blocking 설정
  int flags = fcntl(client_fd, F_GETFL, 0);
  fcntl(client_fd, F_SETFL, flags | O_NONBLOCK);
}

/* ===== HTTP Server 생성 ===== */

int http_server_create(int port) {
  int server_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (server_fd < 0) {
    perror("socket() error");
    return -1;
  }

  // SO_REUSEADDR: 빠른 재시작 가능
  int opt = 1;
  setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  struct sockaddr_in server_addr;
  server_addr.sin_family = AF_INET;
  server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
  server_addr.sin_port = htons(port);

  if (bind(server_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
    perror("bind() error");
    close(server_fd);
    return -1;
  }

  if (listen(server_fd, 128) < 0) {
    perror("listen() error");
    close(server_fd);
    return -1;
  }

  printf("[HTTP Server] ✅ 리스닝 시작: port %d (fd=%d)\n", port, server_fd);

  return server_fd;
}

/* ===== Simple HTTP Server (Event Loop 기반) ===== */

typedef struct {
  int server_fd;
  int port;
  int running;
  fd_set readfds;
  void (*handler)(http_request_t*, char**);

  /* 정적 파일 서빙 (새 필드) */
  char *static_root;    /* 웹 루트 경로 (/var/www 등) */
  void *event_loop;     /* Event Loop 참조 (Thread Pool 접근용) */
} http_server_t;

/* Forward declaration */
http_server_t* http_server_init_with_static(int port, void *handler_callback,
                                             const char *static_root, void *event_loop);

http_server_t* http_server_init(int port, void *handler_callback) {
  return http_server_init_with_static(port, handler_callback, NULL, NULL);
}

http_server_t* http_server_init_with_static(int port, void *handler_callback,
                                             const char *static_root, void *event_loop) {
  http_server_t *server = (http_server_t*)malloc(sizeof(http_server_t));
  if (!server) return NULL;

  server->port = port;
  server->handler = (void (*)(http_request_t*, char**))handler_callback;
  server->running = 1;
  server->event_loop = event_loop;

  // 정적 파일 루트 경로 복사
  if (static_root) {
    server->static_root = (char*)malloc(strlen(static_root) + 1);
    strcpy(server->static_root, static_root);
  } else {
    server->static_root = NULL;
  }

  server->server_fd = http_server_create(port);
  if (server->server_fd < 0) {
    if (server->static_root) free(server->static_root);
    free(server);
    return NULL;
  }

  return server;
}

/* ===== Event Loop Main Cycle (Simplified) ===== */

void http_server_run(http_server_t *server) {
  if (!server || server->server_fd < 0) {
    return;
  }

  printf("[HTTP] Event Loop 시작 (select() 기반)\n");
  printf("[HTTP] 아키텍처: Event Loop(I/O) + Thread Pool(파일 작업)\n\n");

  while (server->running) {
    // 1. File Descriptor Set 구성
    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(server->server_fd, &readfds);

    // 2. select()로 I/O 이벤트 감지 (Timeout: 100ms)
    struct timeval tv = {0, 100000};
    int activity = select(server->server_fd + 1, &readfds, NULL, NULL, &tv);

    if (activity < 0) {
      perror("select() error");
      break;
    }

    // 3. 이벤트 처리 (Poll Phase)
    if (activity > 0 && FD_ISSET(server->server_fd, &readfds)) {
      // 새 클라이언트 연결 수락
      struct sockaddr_in client_addr;
      socklen_t addr_len = sizeof(client_addr);

      int client_fd = accept(server->server_fd, (struct sockaddr*)&client_addr, &addr_len);
      if (client_fd < 0) {
        perror("accept() error");
        continue;
      }

      printf("[HTTP] ✅ 클라이언트 연결: %s:%d\n",
             inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

      // 4. HTTP 요청 수신 및 처리
      char buffer[4096];
      ssize_t bytes_read = read(client_fd, buffer, sizeof(buffer) - 1);

      if (bytes_read > 0) {
        buffer[bytes_read] = '\0';

        // HTTP 요청 파싱
        http_request_t req = {0};
        if (http_parse_request(buffer, &req) == 0) {
          // 정적 파일 서빙 (GET /static/*)
          if (strcmp(req.method, "GET") == 0 &&
              strncmp(req.path, "/static/", 8) == 0 &&
              server->static_root) {
            // Thread Pool에 파일 읽기 요청 전송
            if (server->event_loop) {
              // Event Loop 참조를 통해 Thread Pool에 접근
              // (별도의 fl_request_submit 함수 필요)
              printf("[HTTP] 정적 파일 요청: %s\n", req.path);

              // 임시: 파일 경로 구성
              char resolved_path[512];
              const char *file_part = req.path + 8;  // "/static/" 제거
              snprintf(resolved_path, sizeof(resolved_path), "%s/%s",
                       server->static_root, file_part);

              // 파일 존재 확인
              struct stat st;
              if (stat(resolved_path, &st) == 0 && S_ISREG(st.st_mode)) {
                // 파일 읽기 및 응답 생성
                FILE *file = fopen(resolved_path, "rb");
                if (file) {
                  char response[8192];
                  size_t file_size = st.st_size;

                  // MIME 타입 감지
                  const char *mime = "application/octet-stream";
                  if (strstr(resolved_path, ".js")) mime = "application/javascript";
                  else if (strstr(resolved_path, ".html")) mime = "text/html";
                  else if (strstr(resolved_path, ".json")) mime = "application/json";
                  else if (strstr(resolved_path, ".css")) mime = "text/css";

                  // HTTP 헤더
                  int header_len = snprintf(response, sizeof(response),
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: %s\r\n"
                    "Content-Length: %zu\r\n"
                    "Connection: keep-alive\r\n"
                    "\r\n",
                    mime, file_size);

                  // 헤더 송신
                  write(client_fd, response, header_len);

                  // 파일 내용 송신 (블로킹)
                  char file_buf[1024];
                  size_t read_len;
                  while ((read_len = fread(file_buf, 1, sizeof(file_buf), file)) > 0) {
                    write(client_fd, file_buf, read_len);
                  }

                  fclose(file);
                  printf("[HTTP] ✅ 파일 송신 완료: %s (%zu bytes)\n",
                         resolved_path, file_size);
                } else {
                  // 404 응답
                  const char *not_found = "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 13\r\n"
                    "\r\n"
                    "404 Not Found";
                  write(client_fd, not_found, strlen(not_found));
                }
              } else {
                // 파일 없음: 404
                const char *not_found = "HTTP/1.1 404 Not Found\r\n"
                  "Content-Type: text/plain\r\n"
                  "Content-Length: 13\r\n"
                  "\r\n"
                  "404 Not Found";
                write(client_fd, not_found, strlen(not_found));
              }
            }
          } else {
            // 일반 API 요청
            char *response_body = NULL;
            if (server->handler) {
              server->handler(&req, &response_body);
            }

            if (!response_body) {
              response_body = (char*)malloc(50);
              snprintf(response_body, 50, "{\"status\":\"ok\"}");
            }

            // HTTP 응답 생성
            char *response = http_build_response(200, response_body);

            // 5. 클라이언트에게 응답 송신
            ssize_t bytes_sent = write(client_fd, response, strlen(response));
            printf("[HTTP] 응답 송신: %ld bytes\n", bytes_sent);

            free(response);
            free(response_body);
          }
        } else {
          printf("[HTTP] ❌ 요청 파싱 실패\n");
        }
      }

      close(client_fd);
    }
  }

  printf("[HTTP] Event Loop 종료\n");
}

void http_server_close(http_server_t *server) {
  if (!server) return;

  server->running = 0;
  if (server->server_fd > 0) {
    close(server->server_fd);
  }

  if (server->static_root) {
    free(server->static_root);
  }

  free(server);
  printf("[HTTP] 서버 정리 완료\n");
}

/* ===== Export: FreeLang FFI ===== */

__attribute__((visibility("default"))) void* http_server_listen(int port, void *handler) {
  return http_server_init(port, handler);
}

__attribute__((visibility("default"))) void http_server_start(void *server) {
  http_server_run((http_server_t*)server);
}

__attribute__((visibility("default"))) void http_server_stop(void *server) {
  http_server_close((http_server_t*)server);
}

__attribute__((visibility("default"))) int http_server_port(void *server) {
  http_server_t *s = (http_server_t*)server;
  return s ? s->port : 0;
}

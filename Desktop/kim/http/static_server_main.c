/**
 * FreeLang Static File Server - Standalone Binary
 *
 * 사용법:
 *   ./static-server <port> <root_path>
 *
 * 예:
 *   ./static-server 8080 /var/www
 *   ./static-server 3000 ./public
 *
 * 클라이언트:
 *   curl http://localhost:8080/static/index.html
 *   curl http://localhost:8080/static/app.js
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <sys/stat.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>

/* ===== Static Server 구조체 ===== */

typedef struct {
  int server_fd;
  int port;
  char *static_root;
  int running;
} static_server_t;

static static_server_t *g_server = NULL;

/* ===== Signal Handlers ===== */

void signal_handler(int sig) {
  if (sig == SIGINT || sig == SIGTERM) {
    printf("\n[SERVER] Graceful shutdown...\n");
    if (g_server) {
      g_server->running = 0;
    }
  }
}

/* ===== Server 생성 ===== */

static_server_t* static_server_create(int port, const char *root) {
  static_server_t *server = (static_server_t*)malloc(sizeof(static_server_t));
  if (!server) return NULL;

  // 루트 경로 검증
  struct stat st;
  if (stat(root, &st) != 0 || !S_ISDIR(st.st_mode)) {
    fprintf(stderr, "[ERROR] 웹 루트 경로가 없음: %s\n", root);
    free(server);
    return NULL;
  }

  // TCP 소켓 생성
  int server_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (server_fd < 0) {
    perror("socket() error");
    free(server);
    return NULL;
  }

  // SO_REUSEADDR: 빠른 재시작
  int opt = 1;
  setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  // 바인드
  struct sockaddr_in addr;
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_ANY);
  addr.sin_port = htons(port);

  if (bind(server_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
    perror("bind() error");
    close(server_fd);
    free(server);
    return NULL;
  }

  // 리스닝
  if (listen(server_fd, 128) < 0) {
    perror("listen() error");
    close(server_fd);
    free(server);
    return NULL;
  }

  server->server_fd = server_fd;
  server->port = port;
  server->static_root = (char*)malloc(strlen(root) + 1);
  strcpy(server->static_root, root);
  server->running = 1;

  printf("[SERVER] ✅ 정적 파일 서버 시작\n");
  printf("         포트: %d\n", port);
  printf("         경로: %s\n", root);
  printf("         URI: http://localhost:%d/static/<filename>\n\n", port);

  return server;
}

/* ===== 파일 서빙 ===== */

void handle_client(int client_fd, const char *root) {
  char buffer[4096];
  ssize_t bytes_read = read(client_fd, buffer, sizeof(buffer) - 1);

  if (bytes_read <= 0) {
    close(client_fd);
    return;
  }

  buffer[bytes_read] = '\0';

  // HTTP 요청 파싱
  char method[16], path[512];
  sscanf(buffer, "%15s %511s", method, path);

  printf("[HTTP] %s %s\n", method, path);

  // GET /static/* 확인
  if (strcmp(method, "GET") != 0 || strncmp(path, "/static/", 8) != 0) {
    // 404
    const char *response = "HTTP/1.1 404 Not Found\r\n"
      "Content-Type: text/plain\r\n"
      "Content-Length: 13\r\n"
      "\r\n"
      "404 Not Found";
    write(client_fd, response, strlen(response));
    close(client_fd);
    return;
  }

  // 파일 경로 구성
  char filepath[512];
  const char *filename = path + 8;  // "/static/" 제거

  // 경로 검증
  if (filename[0] == '.' || strstr(filename, "..") != NULL) {
    // 보안: 상위 경로 및 dotfile 거부
    const char *response = "HTTP/1.1 403 Forbidden\r\n"
      "Content-Type: text/plain\r\n"
      "Content-Length: 13\r\n"
      "\r\n"
      "403 Forbidden";
    write(client_fd, response, strlen(response));
    close(client_fd);
    return;
  }

  snprintf(filepath, sizeof(filepath), "%s/%s", root, filename);

  // 파일 존재 확인
  struct stat st;
  if (stat(filepath, &st) != 0 || !S_ISREG(st.st_mode)) {
    // 404
    const char *response = "HTTP/1.1 404 Not Found\r\n"
      "Content-Type: text/plain\r\n"
      "Content-Length: 13\r\n"
      "\r\n"
      "404 Not Found";
    write(client_fd, response, strlen(response));
    close(client_fd);
    return;
  }

  // 파일 크기
  off_t file_size = st.st_size;

  // MIME 타입 감지
  const char *mime = "application/octet-stream";
  if (strstr(filename, ".html")) mime = "text/html";
  else if (strstr(filename, ".htm")) mime = "text/html";
  else if (strstr(filename, ".js")) mime = "application/javascript";
  else if (strstr(filename, ".json")) mime = "application/json";
  else if (strstr(filename, ".css")) mime = "text/css";
  else if (strstr(filename, ".txt")) mime = "text/plain";
  else if (strstr(filename, ".jpg")) mime = "image/jpeg";
  else if (strstr(filename, ".jpeg")) mime = "image/jpeg";
  else if (strstr(filename, ".png")) mime = "image/png";
  else if (strstr(filename, ".gif")) mime = "image/gif";
  else if (strstr(filename, ".svg")) mime = "image/svg+xml";
  else if (strstr(filename, ".pdf")) mime = "application/pdf";
  else if (strstr(filename, ".xml")) mime = "text/xml";

  // HTTP 헤더 작성
  char header[512];
  int header_len = snprintf(header, sizeof(header),
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: %s\r\n"
    "Content-Length: %lld\r\n"
    "Connection: keep-alive\r\n"
    "Cache-Control: max-age=3600\r\n"
    "\r\n",
    mime, (long long)file_size);

  // 헤더 송신
  write(client_fd, header, header_len);

  // 파일 내용 송신
  FILE *file = fopen(filepath, "rb");
  if (file) {
    char file_buf[4096];
    size_t read_len;
    size_t total_sent = 0;

    while ((read_len = fread(file_buf, 1, sizeof(file_buf), file)) > 0) {
      ssize_t sent = write(client_fd, file_buf, read_len);
      if (sent > 0) {
        total_sent += sent;
      }
    }

    fclose(file);
    printf("[SENT] %s: %zu bytes\n", filename, total_sent);
  }

  close(client_fd);
}

/* ===== Event Loop ===== */

void static_server_run(static_server_t *server) {
  while (server->running) {
    // 1. select()로 들어오는 연결 감지
    fd_set readfds;
    FD_ZERO(&readfds);
    FD_SET(server->server_fd, &readfds);

    struct timeval tv = {0, 100000};  // 100ms timeout
    int activity = select(server->server_fd + 1, &readfds, NULL, NULL, &tv);

    if (activity < 0) {
      perror("select() error");
      break;
    }

    // 2. 새 클라이언트 수락
    if (activity > 0 && FD_ISSET(server->server_fd, &readfds)) {
      struct sockaddr_in client_addr;
      socklen_t addr_len = sizeof(client_addr);

      int client_fd = accept(server->server_fd, (struct sockaddr*)&client_addr, &addr_len);
      if (client_fd < 0) {
        perror("accept() error");
        continue;
      }

      printf("[CLIENT] %s:%d (fd=%d)\n",
             inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port), client_fd);

      // 3. 클라이언트 처리 (파일 서빙)
      handle_client(client_fd, server->static_root);
    }
  }

  printf("[SERVER] Event Loop 종료\n");
}

void static_server_close(static_server_t *server) {
  if (!server) return;

  close(server->server_fd);
  if (server->static_root) {
    free(server->static_root);
  }
  free(server);

  printf("[SERVER] 정리 완료\n");
}

/* ===== Main ===== */

void print_usage(const char *prog) {
  fprintf(stderr, "사용법: %s <port> <root_path>\n", prog);
  fprintf(stderr, "예: %s 8080 ./public\n", prog);
  fprintf(stderr, "    %s 3000 /var/www\n", prog);
}

int main(int argc, char *argv[]) {
  if (argc != 3) {
    print_usage(argv[0]);
    return 1;
  }

  int port = atoi(argv[1]);
  const char *root = argv[2];

  if (port <= 0 || port > 65535) {
    fprintf(stderr, "[ERROR] 잘못된 포트: %s\n", argv[1]);
    return 1;
  }

  // 서버 생성
  g_server = static_server_create(port, root);
  if (!g_server) {
    return 1;
  }

  // Signal handler 등록
  signal(SIGINT, signal_handler);
  signal(SIGTERM, signal_handler);

  // Event Loop 실행
  static_server_run(g_server);

  // 정리
  static_server_close(g_server);
  g_server = NULL;

  return 0;
}

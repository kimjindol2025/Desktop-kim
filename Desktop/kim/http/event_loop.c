/**
 * FreeLang Event Loop Implementation
 * Based on libuv architecture: Event Loop + Thread Pool
 *
 * 메커니즘:
 * 1. Event Loop: 커널의 select/epoll으로 I/O 이벤트 감지
 * 2. Thread Pool: 파일/DNS 등 비동기 미지원 작업 처리
 * 3. Handles/Requests: C 구조체로 상태 관리
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
#include <time.h>

/* Phase 17: libuv integration */
#ifdef FREELANG_FFI_ENABLE
#include "freelang_ffi.h"
#endif

/* ===== Handle & Request 기본 구조 ===== */

/* Forward declarations */
struct fl_loop;
struct fl_handle;
struct fl_request;

typedef struct fl_loop fl_loop_t;
typedef struct fl_handle fl_handle_t;
typedef struct fl_request fl_request_t;

/* Request: 단일 작업 (데이터 송수신, 파일 읽기) */
struct fl_request {
  int type;                /* REQUEST_READ(1), REQUEST_WRITE(2), REQUEST_FILE_READ(3) */
  int fd;                  /* 소켓 FD (네트워크 I/O) */
  void (*callback)(struct fl_request*);
  void *data;
  char buffer[4096];
  ssize_t result;

  /* REQUEST_FILE_READ용 필드 */
  char *file_path;         /* 읽을 파일 경로 */
  char *response_buffer;   /* 완성된 HTTP 응답 (헤더 + 바디) */
  size_t response_len;     /* 응답 크기 */
  int client_fd;           /* 응답 전송할 소켓 */
};

/* Handle: 수명이 긴 객체 (TCP 서버, 타이머) */
struct fl_handle {
  int fd;                  /* File descriptor */
  int type;                /* HANDLE_TCP_SERVER, HANDLE_TIMER */
  void (*callback)(struct fl_handle*);
  void *data;
  time_t last_check;
};

/* Event Loop: 전체 이벤트 루프 구조 */
struct fl_loop {
  int running;
  int max_handles;
  struct fl_handle **handles;
  int handle_count;

  /* Thread Pool */
  int thread_count;
  pthread_t *threads;
  pthread_mutex_t queue_mutex;
  pthread_cond_t queue_cond;
  struct fl_request *request_queue;
  int queue_size;
  int queue_capacity;

  /* 마지막 실행 시간 (타이머용) */
  time_t last_time;

  /* Phase 17: libuv integration */
#ifdef FREELANG_FFI_ENABLE
  fl_event_context_t *ffi_context;  /* FFI context for async timers/callbacks */
#endif
};

/* ===== Event Loop 초기화 ===== */

fl_loop_t* fl_loop_create(int thread_count) {
  fl_loop_t *loop = (fl_loop_t*)malloc(sizeof(fl_loop_t));
  if (!loop) return NULL;

  loop->running = 0;
  loop->max_handles = 256;
  loop->handles = (fl_handle_t**)malloc(sizeof(fl_handle_t*) * loop->max_handles);
  loop->handle_count = 0;

  loop->thread_count = thread_count > 0 ? thread_count : 4;
  loop->threads = (pthread_t*)malloc(sizeof(pthread_t) * loop->thread_count);
  pthread_mutex_init(&loop->queue_mutex, NULL);
  pthread_cond_init(&loop->queue_cond, NULL);
  loop->request_queue = NULL;
  loop->queue_size = 0;
  loop->queue_capacity = 0;

  loop->last_time = time(NULL);

#ifdef FREELANG_FFI_ENABLE
  /* Initialize FFI context for timers */
  loop->ffi_context = freelang_event_context_create();
  if (loop->ffi_context) {
    printf("[Event Loop] FFI context initialized (libuv timers enabled)\n");
  }
#endif

  printf("[Event Loop] 초기화 완료 (Thread Pool: %d)\n", loop->thread_count);

  return loop;
}

/* ===== Thread Pool: Worker Thread ===== */

void* fl_worker_thread(void *arg) {
  fl_loop_t *loop = (fl_loop_t*)arg;

  while (loop->running) {
    pthread_mutex_lock(&loop->queue_mutex);

    // 요청이 없으면 대기
    while (loop->queue_size == 0 && loop->running) {
      pthread_cond_wait(&loop->queue_cond, &loop->queue_mutex);
    }

    if (!loop->running) {
      pthread_mutex_unlock(&loop->queue_mutex);
      break;
    }

    // 요청 꺼내기
    if (loop->queue_size > 0) {
      fl_request_t *req = &loop->request_queue[0];

      // 요청 처리 (실제 작업)
      if (req->type == 1) {  // REQUEST_READ
        req->result = read(req->fd, req->buffer, sizeof(req->buffer));
      } else if (req->type == 2) {  // REQUEST_WRITE
        req->result = write(req->fd, req->buffer, strlen(req->buffer));
      } else if (req->type == 3) {  // REQUEST_FILE_READ
        // 파일 읽기 + HTTP 응답 생성 (블로킹 가능)
        FILE *file = fopen(req->file_path, "rb");
        if (!file) {
          // 파일 없음 → 404 응답
          req->response_buffer = (char*)malloc(256);
          snprintf(req->response_buffer, 256,
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: keep-alive\r\n"
            "\r\n"
            "404 Not Found");
          req->response_len = strlen(req->response_buffer);
        } else {
          // 파일 존재 → 내용 읽기
          struct stat st;
          stat(req->file_path, &st);
          off_t file_size = st.st_size;

          // 응답 버퍼 할당 (헤더 + 바디)
          req->response_buffer = (char*)malloc(4096 + file_size);
          if (!req->response_buffer) {
            fclose(file);
            goto file_read_error;
          }

          // MIME 타입 감지 (간단 버전)
          const char *mime = "application/octet-stream";
          if (strstr(req->file_path, ".js")) mime = "application/javascript";
          else if (strstr(req->file_path, ".html")) mime = "text/html";
          else if (strstr(req->file_path, ".json")) mime = "application/json";
          else if (strstr(req->file_path, ".css")) mime = "text/css";
          else if (strstr(req->file_path, ".txt")) mime = "text/plain";
          else if (strstr(req->file_path, ".jpg")) mime = "image/jpeg";
          else if (strstr(req->file_path, ".png")) mime = "image/png";

          // HTTP 헤더 생성
          int header_len = snprintf(req->response_buffer, 4096,
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: %s\r\n"
            "Content-Length: %lld\r\n"
            "Connection: keep-alive\r\n"
            "Cache-Control: max-age=3600\r\n"
            "\r\n",
            mime, (long long)file_size);

          // 파일 내용 읽기
          size_t read_len = fread(req->response_buffer + header_len, 1, file_size, file);
          if (read_len != (size_t)file_size) {
            fclose(file);
            goto file_read_error;
          }

          req->response_len = header_len + file_size;
          fclose(file);
        }
        req->result = req->response_len;
      }

      file_read_error:

      // 콜백 실행
      if (req->callback) {
        req->callback(req);
      }

      // 요청 제거
      memmove(loop->request_queue, loop->request_queue + 1,
              (loop->queue_size - 1) * sizeof(fl_request_t));
      loop->queue_size--;
    }

    pthread_mutex_unlock(&loop->queue_mutex);
  }

  return NULL;
}

/* ===== Event Loop: 메인 루프 ===== */

void fl_loop_run(fl_loop_t *loop) {
  loop->running = 1;

  // Thread Pool 시작
  for (int i = 0; i < loop->thread_count; i++) {
    pthread_create(&loop->threads[i], NULL, fl_worker_thread, loop);
  }

  printf("[Event Loop] 시작 (select() 기반)\n");

  // ===== Event Loop: Main Cycle =====
  while (loop->running) {
    // 1. select()로 I/O 이벤트 감지
    fd_set readfds, writefds;
    FD_ZERO(&readfds);
    FD_ZERO(&writefds);

    int max_fd = 0;
    for (int i = 0; i < loop->handle_count; i++) {
      fl_handle_t *handle = loop->handles[i];
      if (handle && handle->fd > 0) {
        FD_SET(handle->fd, &readfds);
        if (handle->fd > max_fd) max_fd = handle->fd;
      }
    }

    // Timeout: 100ms
    struct timeval tv = {0, 100000};
    int activity = select(max_fd + 1, &readfds, &writefds, NULL, &tv);

    if (activity < 0) {
      perror("select() error");
      break;
    }

    // 2. libuv events (Phase 17)
#ifdef FREELANG_FFI_ENABLE
    if (loop->ffi_context) {
      freelang_event_loop_run(loop->ffi_context, 0);  /* Non-blocking */
    }
#endif

    // 3. I/O 이벤트 처리 (Poll Phase)
    if (activity > 0) {
      for (int i = 0; i < loop->handle_count; i++) {
        fl_handle_t *handle = loop->handles[i];
        if (handle && handle->fd > 0 && FD_ISSET(handle->fd, &readfds)) {
          if (handle->callback) {
            handle->callback(handle);
          }
        }
      }
    }

    // 4. Callback Queue Processing (Phase 17)
#ifdef FREELANG_FFI_ENABLE
    if (loop->ffi_context) {
      freelang_process_callbacks(loop->ffi_context);
    }
#endif

    // 5. Timer 처리
    time_t now = time(NULL);
    if (now != loop->last_time) {
      loop->last_time = now;
      // Timer 콜백들 실행
      for (int i = 0; i < loop->handle_count; i++) {
        fl_handle_t *handle = loop->handles[i];
        if (handle && handle->type == 2) {  // HANDLE_TIMER
          if (handle->callback) {
            handle->callback(handle);
          }
        }
      }
    }
  }

  printf("[Event Loop] 종료\n");
}

/* ===== Event Loop 정리 ===== */

void fl_loop_close(fl_loop_t *loop) {
  if (!loop) return;

  loop->running = 0;

#ifdef FREELANG_FFI_ENABLE
  /* Cleanup FFI context */
  if (loop->ffi_context) {
    freelang_event_loop_stop(loop->ffi_context);
    freelang_event_context_destroy(loop->ffi_context);
    loop->ffi_context = NULL;
  }
#endif

  // 모든 스레드 종료 대기
  for (int i = 0; i < loop->thread_count; i++) {
    pthread_join(loop->threads[i], NULL);
  }

  pthread_mutex_destroy(&loop->queue_mutex);
  pthread_cond_destroy(&loop->queue_cond);

  free(loop->threads);
  free(loop->handles);
  free(loop->request_queue);
  free(loop);

  printf("[Event Loop] 정리 완료\n");
}

/* ===== Handle 관리 ===== */

fl_handle_t* fl_handle_new(fl_loop_t *loop, int fd, int type) {
  if (loop->handle_count >= loop->max_handles) {
    return NULL;
  }

  fl_handle_t *handle = (fl_handle_t*)malloc(sizeof(fl_handle_t));
  if (!handle) return NULL;

  handle->fd = fd;
  handle->type = type;
  handle->callback = NULL;
  handle->data = NULL;
  handle->last_check = time(NULL);

  loop->handles[loop->handle_count++] = handle;

  return handle;
}

void fl_handle_free(fl_loop_t *loop, fl_handle_t *handle) {
  if (!handle) return;

  for (int i = 0; i < loop->handle_count; i++) {
    if (loop->handles[i] == handle) {
      memmove(&loop->handles[i], &loop->handles[i + 1],
              (loop->handle_count - i - 1) * sizeof(fl_handle_t*));
      loop->handle_count--;
      break;
    }
  }

  free(handle);
}

/* ===== Request 큐에 추가 ===== */

void fl_request_submit(fl_loop_t *loop, fl_request_t *req) {
  pthread_mutex_lock(&loop->queue_mutex);

  if (loop->queue_size >= loop->queue_capacity) {
    loop->queue_capacity = loop->queue_capacity > 0 ? loop->queue_capacity * 2 : 10;
    loop->request_queue = (fl_request_t*)realloc(loop->request_queue,
                                                  loop->queue_capacity * sizeof(fl_request_t));
  }

  memcpy(&loop->request_queue[loop->queue_size], req, sizeof(fl_request_t));
  loop->queue_size++;

  pthread_cond_signal(&loop->queue_cond);
  pthread_mutex_unlock(&loop->queue_mutex);
}

/* ===== Export: FreeLang FFI ===== */

__attribute__((visibility("default"))) void* fl_loop_create_export(int threads) {
  return fl_loop_create(threads);
}

__attribute__((visibility("default"))) void fl_loop_run_export(void *loop) {
  fl_loop_run((fl_loop_t*)loop);
}

__attribute__((visibility("default"))) void fl_loop_close_export(void *loop) {
  fl_loop_close((fl_loop_t*)loop);
}

__attribute__((visibility("default"))) void* fl_handle_new_export(void *loop, int fd, int type) {
  return fl_handle_new((fl_loop_t*)loop, fd, type);
}

/**
 * Phase 38: Event Loop Migration - epoll Implementation
 * FreeLang v2 - High-Performance Event Loop using Linux epoll
 *
 * Improvement over select():
 * - select() is O(n) - iterate all FDs
 * - epoll is O(1) - event notification
 *
 * Expected Impact:
 * - Reduce latency for 1000+ connections
 * - Improve throughput 5-10x with many connections
 * - Better CPU efficiency (no full FD scan)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/epoll.h>
#include <netinet/in.h>
#include <pthread.h>
#include <time.h>
#include <errno.h>

// ===== Configuration =====
#define MAX_EVENTS 1024
#define MAX_CONNECTIONS 10000
#define EPOLL_TIMEOUT 100  // milliseconds
#define THREAD_POOL_SIZE 8

// ===== Connection Structure =====
typedef enum {
  CONN_IDLE,
  CONN_READING_HEADER,
  CONN_READING_BODY,
  CONN_PROCESSING,
  CONN_WRITING,
  CONN_CLOSING
} conn_state_t;

typedef struct {
  int fd;
  conn_state_t state;
  time_t created_at;
  time_t last_activity;
  int keep_alive;
  char *request_buf;
  char *response_buf;
  int request_len;
  int response_len;
  int bytes_sent;
} connection_t;

// ===== Event Loop Structure (epoll) =====
typedef struct {
  int epoll_fd;
  int listen_fd;
  int port;
  int running;

  connection_t connections[MAX_CONNECTIONS];
  pthread_mutex_t conn_lock;
  int active_conn_count;

  struct epoll_event events[MAX_EVENTS];

  // Statistics
  long total_events;
  long total_reads;
  long total_writes;
  long total_connections;
  long peak_connections;
} epoll_loop_t;

// ===== Event Loop Implementation =====

epoll_loop_t* epoll_loop_create(int port) {
  epoll_loop_t *loop = (epoll_loop_t*)malloc(sizeof(epoll_loop_t));

  loop->port = port;
  loop->running = 0;
  loop->active_conn_count = 0;
  loop->total_events = 0;
  loop->total_reads = 0;
  loop->total_writes = 0;
  loop->total_connections = 0;
  loop->peak_connections = 0;

  pthread_mutex_init(&loop->conn_lock, NULL);

  // Initialize connections
  for (int i = 0; i < MAX_CONNECTIONS; i++) {
    loop->connections[i].fd = -1;
    loop->connections[i].state = CONN_IDLE;
    loop->connections[i].request_buf = (char*)malloc(4096);
    loop->connections[i].response_buf = (char*)malloc(8192);
  }

  // Create epoll instance
  loop->epoll_fd = epoll_create1(EPOLL_CLOEXEC);
  if (loop->epoll_fd < 0) {
    perror("epoll_create1");
    return NULL;
  }

  // Create listen socket
  loop->listen_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (loop->listen_fd < 0) {
    perror("socket");
    return NULL;
  }

  // Enable SO_REUSEADDR
  int opt = 1;
  setsockopt(loop->listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

  // Bind
  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_ANY);
  addr.sin_port = htons(port);

  if (bind(loop->listen_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
    perror("bind");
    return NULL;
  }

  // Listen
  listen(loop->listen_fd, 128);

  // Set non-blocking
  fcntl(loop->listen_fd, F_SETFL, O_NONBLOCK);

  // Register listen socket with epoll
  struct epoll_event ev;
  ev.events = EPOLLIN;
  ev.data.fd = loop->listen_fd;

  if (epoll_ctl(loop->epoll_fd, EPOLL_CTL_ADD, loop->listen_fd, &ev) < 0) {
    perror("epoll_ctl");
    return NULL;
  }

  fprintf(stderr, "[EPOLL] Event loop created (fd=%d, port=%d)\n", loop->epoll_fd, port);
  fprintf(stderr, "[EPOLL] Max connections: %d\n", MAX_CONNECTIONS);
  fprintf(stderr, "[EPOLL] Epoll timeout: %dms\n", EPOLL_TIMEOUT);

  return loop;
}

// Accept new connection
int epoll_accept_connection(epoll_loop_t *loop) {
  struct sockaddr_in client_addr;
  socklen_t client_len = sizeof(client_addr);

  int client_fd = accept(loop->listen_fd, (struct sockaddr*)&client_addr, &client_len);
  if (client_fd < 0) {
    if (errno != EAGAIN && errno != EWOULDBLOCK) {
      perror("accept");
    }
    return -1;
  }

  // Set non-blocking
  fcntl(client_fd, F_SETFL, O_NONBLOCK);

  // Find free connection slot
  pthread_mutex_lock(&loop->conn_lock);

  int conn_idx = -1;
  for (int i = 0; i < MAX_CONNECTIONS; i++) {
    if (loop->connections[i].fd == -1) {
      conn_idx = i;
      break;
    }
  }

  if (conn_idx == -1) {
    pthread_mutex_unlock(&loop->conn_lock);
    fprintf(stderr, "[EPOLL] Connection limit reached, rejecting\n");
    close(client_fd);
    return -1;
  }

  // Register connection
  connection_t *conn = &loop->connections[conn_idx];
  conn->fd = client_fd;
  conn->state = CONN_IDLE;
  conn->created_at = time(NULL);
  conn->last_activity = time(NULL);
  conn->keep_alive = 1;
  conn->request_len = 0;
  conn->response_len = 0;
  conn->bytes_sent = 0;

  loop->active_conn_count++;
  loop->total_connections++;
  if (loop->active_conn_count > loop->peak_connections) {
    loop->peak_connections = loop->active_conn_count;
  }

  pthread_mutex_unlock(&loop->conn_lock);

  // Add to epoll (watch for read events)
  struct epoll_event ev;
  ev.events = EPOLLIN | EPOLLERR | EPOLLHUP;
  ev.data.fd = client_fd;

  epoll_ctl(loop->epoll_fd, EPOLL_CTL_ADD, client_fd, &ev);

  return client_fd;
}

// Process events
void epoll_process_events(epoll_loop_t *loop, struct epoll_event *events, int nfds) {
  loop->total_events += nfds;

  for (int i = 0; i < nfds; i++) {
    int fd = events[i].data.fd;

    // Accept new connection
    if (fd == loop->listen_fd) {
      epoll_accept_connection(loop);
      continue;
    }

    // Handle client connection
    if (events[i].events & EPOLLIN) {
      // Read event
      loop->total_reads++;

      // Find connection
      for (int j = 0; j < MAX_CONNECTIONS; j++) {
        if (loop->connections[j].fd == fd) {
          connection_t *conn = &loop->connections[j];

          // Read request
          int n = read(fd, conn->request_buf + conn->request_len,
                      4096 - conn->request_len);

          if (n > 0) {
            conn->request_len += n;
            conn->last_activity = time(NULL);

            // Check if complete HTTP request (simplified)
            if (strstr(conn->request_buf, "\r\n\r\n")) {
              conn->state = CONN_PROCESSING;

              // Generate response
              sprintf(conn->response_buf,
                     "HTTP/1.1 200 OK\r\n"
                     "Content-Type: text/plain\r\n"
                     "Content-Length: 2\r\n"
                     "Connection: keep-alive\r\n"
                     "\r\n"
                     "OK");
              conn->response_len = strlen(conn->response_buf);
              conn->bytes_sent = 0;

              // Switch to write mode
              struct epoll_event ev;
              ev.events = EPOLLOUT | EPOLLERR | EPOLLHUP;
              ev.data.fd = fd;
              epoll_ctl(loop->epoll_fd, EPOLL_CTL_MOD, fd, &ev);
            }
          } else if (n == 0 || (n < 0 && errno != EAGAIN)) {
            // Connection closed
            epoll_ctl(loop->epoll_fd, EPOLL_CTL_DEL, fd, NULL);
            close(fd);
            conn->fd = -1;
            loop->active_conn_count--;
          }
          break;
        }
      }
    }

    if (events[i].events & EPOLLOUT) {
      // Write event
      loop->total_writes++;

      // Find connection
      for (int j = 0; j < MAX_CONNECTIONS; j++) {
        if (loop->connections[j].fd == fd) {
          connection_t *conn = &loop->connections[j];

          // Send response
          int to_send = conn->response_len - conn->bytes_sent;
          int n = write(fd, conn->response_buf + conn->bytes_sent, to_send);

          if (n > 0) {
            conn->bytes_sent += n;
            conn->last_activity = time(NULL);

            if (conn->bytes_sent >= conn->response_len) {
              // Response complete
              conn->request_len = 0;
              conn->response_len = 0;
              conn->bytes_sent = 0;

              if (conn->keep_alive) {
                // Reset for next request
                conn->state = CONN_IDLE;

                // Switch back to read mode
                struct epoll_event ev;
                ev.events = EPOLLIN | EPOLLERR | EPOLLHUP;
                ev.data.fd = fd;
                epoll_ctl(loop->epoll_fd, EPOLL_CTL_MOD, fd, &ev);
              } else {
                // Close connection
                epoll_ctl(loop->epoll_fd, EPOLL_CTL_DEL, fd, NULL);
                close(fd);
                conn->fd = -1;
                loop->active_conn_count--;
              }
            }
          } else if (n < 0 && errno != EAGAIN) {
            // Error
            epoll_ctl(loop->epoll_fd, EPOLL_CTL_DEL, fd, NULL);
            close(fd);
            conn->fd = -1;
            loop->active_conn_count--;
          }
          break;
        }
      }
    }

    if (events[i].events & (EPOLLERR | EPOLLHUP)) {
      // Error or hangup
      for (int j = 0; j < MAX_CONNECTIONS; j++) {
        if (loop->connections[j].fd == fd) {
          epoll_ctl(loop->epoll_fd, EPOLL_CTL_DEL, fd, NULL);
          close(fd);
          loop->connections[j].fd = -1;
          loop->active_conn_count--;
          break;
        }
      }
    }
  }
}

// Main event loop
int epoll_loop_run(epoll_loop_t *loop) {
  loop->running = 1;

  fprintf(stderr, "[EPOLL] Event loop started (PID: %d)\n", getpid());
  fprintf(stderr, "[EPOLL] Waiting for events (timeout: %dms)...\n", EPOLL_TIMEOUT);

  while (loop->running) {
    int nfds = epoll_wait(loop->epoll_fd, loop->events, MAX_EVENTS, EPOLL_TIMEOUT);

    if (nfds < 0) {
      if (errno != EINTR) {
        perror("epoll_wait");
        break;
      }
      continue;
    }

    if (nfds > 0) {
      epoll_process_events(loop, loop->events, nfds);
    }

    // Periodic cleanup (every 100ms if timeout occurs)
    if (nfds == 0) {
      time_t now = time(NULL);
      pthread_mutex_lock(&loop->conn_lock);

      for (int i = 0; i < MAX_CONNECTIONS; i++) {
        if (loop->connections[i].fd != -1) {
          // Check timeout
          if (now - loop->connections[i].last_activity > 30) {
            epoll_ctl(loop->epoll_fd, EPOLL_CTL_DEL, loop->connections[i].fd, NULL);
            close(loop->connections[i].fd);
            loop->connections[i].fd = -1;
            loop->active_conn_count--;
          }
        }
      }

      pthread_mutex_unlock(&loop->conn_lock);
    }
  }

  return 0;
}

void epoll_loop_stop(epoll_loop_t *loop) {
  loop->running = 0;
}

void epoll_loop_destroy(epoll_loop_t *loop) {
  for (int i = 0; i < MAX_CONNECTIONS; i++) {
    if (loop->connections[i].fd != -1) {
      close(loop->connections[i].fd);
    }
    free(loop->connections[i].request_buf);
    free(loop->connections[i].response_buf);
  }

  close(loop->listen_fd);
  close(loop->epoll_fd);
  pthread_mutex_destroy(&loop->conn_lock);

  fprintf(stderr, "[EPOLL] Statistics:\n");
  fprintf(stderr, "[EPOLL]   Total events: %ld\n", loop->total_events);
  fprintf(stderr, "[EPOLL]   Read events: %ld\n", loop->total_reads);
  fprintf(stderr, "[EPOLL]   Write events: %ld\n", loop->total_writes);
  fprintf(stderr, "[EPOLL]   Total connections: %ld\n", loop->total_connections);
  fprintf(stderr, "[EPOLL]   Peak connections: %ld\n", loop->peak_connections);

  free(loop);
}

// ===== Export: FreeLang FFI =====

__attribute__((visibility("default"))) void* epoll_loop_create_export(int port) {
  return epoll_loop_create(port);
}

__attribute__((visibility("default"))) int epoll_loop_run_export(void *loop_ptr) {
  return epoll_loop_run((epoll_loop_t*)loop_ptr);
}

__attribute__((visibility("default"))) void epoll_loop_stop_export(void *loop_ptr) {
  epoll_loop_stop((epoll_loop_t*)loop_ptr);
}

__attribute__((visibility("default"))) void epoll_loop_destroy_export(void *loop_ptr) {
  epoll_loop_destroy((epoll_loop_t*)loop_ptr);
}

// Statistics export
typedef struct {
  long total_events;
  long total_reads;
  long total_writes;
  long active_connections;
  long peak_connections;
} epoll_stats_t;

__attribute__((visibility("default"))) epoll_stats_t epoll_loop_get_stats_export(void *loop_ptr) {
  epoll_loop_t *loop = (epoll_loop_t*)loop_ptr;
  epoll_stats_t stats;

  pthread_mutex_lock(&loop->conn_lock);
  stats.active_connections = loop->active_conn_count;
  pthread_mutex_unlock(&loop->conn_lock);

  stats.total_events = loop->total_events;
  stats.total_reads = loop->total_reads;
  stats.total_writes = loop->total_writes;
  stats.peak_connections = loop->peak_connections;

  return stats;
}

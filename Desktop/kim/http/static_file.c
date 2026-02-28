/**
 * FreeLang Static File Server - File Handling & Security
 *
 * 역할:
 * 1. 파일 확장자 → MIME 타입 매핑 (30+ 타입)
 * 2. URL → 파일 경로 변환 (경로 검증)
 * 3. 보안: Directory traversal (..) 차단
 * 4. 보안: Dotfile (.env, .htaccess) 차단
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <sys/stat.h>
#include <unistd.h>

/* ===== MIME 타입 매핑 테이블 ===== */

typedef struct {
  const char *extension;
  const char *mime_type;
} mime_type_t;

static const mime_type_t MIME_TYPES[] = {
  /* 텍스트 */
  { ".html", "text/html" },
  { ".htm", "text/html" },
  { ".txt", "text/plain" },
  { ".css", "text/css" },
  { ".xml", "text/xml" },
  { ".csv", "text/csv" },
  { ".md", "text/markdown" },

  /* JavaScript */
  { ".js", "application/javascript" },
  { ".mjs", "application/javascript" },
  { ".json", "application/json" },

  /* 이미지 */
  { ".jpg", "image/jpeg" },
  { ".jpeg", "image/jpeg" },
  { ".png", "image/png" },
  { ".gif", "image/gif" },
  { ".svg", "image/svg+xml" },
  { ".ico", "image/x-icon" },
  { ".webp", "image/webp" },

  /* 비디오/오디오 */
  { ".mp4", "video/mp4" },
  { ".webm", "video/webm" },
  { ".mp3", "audio/mpeg" },
  { ".wav", "audio/wav" },

  /* 문서 */
  { ".pdf", "application/pdf" },
  { ".doc", "application/msword" },
  { ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
  { ".xls", "application/vnd.ms-excel" },
  { ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
  { ".zip", "application/zip" },
  { ".tar", "application/x-tar" },
  { ".gz", "application/gzip" },

  /* 폰트 */
  { ".woff", "font/woff" },
  { ".woff2", "font/woff2" },
  { ".ttf", "font/ttf" },
  { ".otf", "font/otf" },

  /* 기타 */
  { ".wasm", "application/wasm" },

  /* 종료 마커 */
  { NULL, NULL }
};

/**
 * MIME 타입 조회
 *
 * @param filename: 파일명 (예: "app.js")
 * @return: MIME 타입 (예: "application/javascript"), 기본값: "application/octet-stream"
 */
const char* sf_get_mime_type(const char *filename) {
  if (!filename) {
    return "application/octet-stream";
  }

  // 파일명에서 확장자 추출
  const char *dot = strrchr(filename, '.');
  if (!dot) {
    return "application/octet-stream";
  }

  // 매핑 테이블 검색
  for (int i = 0; MIME_TYPES[i].extension != NULL; i++) {
    if (strcasecmp(dot, MIME_TYPES[i].extension) == 0) {
      return MIME_TYPES[i].mime_type;
    }
  }

  return "application/octet-stream";
}

/**
 * Dotfile 검사 (.env, .htaccess, .git 등 차단)
 *
 * @param filename: 파일명
 * @return: true면 dotfile (차단), false면 정상 파일
 */
bool sf_is_dotfile(const char *filename) {
  if (!filename || filename[0] == '\0') {
    return false;
  }

  // 파일명의 마지막 경로 구분자 이후 부분 추출
  const char *basename = strrchr(filename, '/');
  if (!basename) {
    basename = filename;
  } else {
    basename++;  // '/' 다음부터
  }

  // 점(.)으로 시작하면 dotfile
  return basename[0] == '.';
}

/**
 * 경로 안전성 검사 (directory traversal 차단)
 *
 * @param path: 파일 경로
 * @return: true면 안전, false면 위험 (.., 절대경로 등)
 */
bool sf_is_safe_path(const char *path) {
  if (!path || path[0] == '\0') {
    return false;
  }

  // 절대 경로 거부
  if (path[0] == '/') {
    return false;
  }

  // ".." 검사 (directory traversal)
  if (strstr(path, "..") != NULL) {
    return false;
  }

  // 각 경로 컴포넌트 검사
  char *path_copy = strdup(path);
  if (!path_copy) return false;

  bool result = true;
  char *saveptr;
  char *component = strtok_r(path_copy, "/", &saveptr);

  while (component != NULL) {
    // 빈 컴포넌트 또는 점 거부
    if (component[0] == '\0' || strcmp(component, ".") == 0) {
      result = false;
      break;
    }

    component = strtok_r(NULL, "/", &saveptr);
  }

  free(path_copy);
  return result;
}

/**
 * URL 경로를 파일 시스템 경로로 변환
 *
 * 예: URL "/static/app.js" + root "/var/www" → "/var/www/app.js"
 *
 * @param url_path: URL 경로 (예: "/static/app.js")
 * @param root: 웹 루트 경로 (예: "/var/www")
 * @param resolved_path: 변환된 경로 저장 (출력)
 * @param size: resolved_path 버퍼 크기
 * @return: 성공(0), 실패(-1)
 */
int sf_resolve_path(const char *url_path, const char *root,
                    char *resolved_path, size_t size) {
  if (!url_path || !root || !resolved_path) {
    return -1;
  }

  // 1. "/static/app.js" 형태인지 검사
  if (url_path[0] != '/') {
    return -1;
  }

  // 2. "/static/" 프리픽스 제거
  const char *file_part = url_path + 1;  // "/" 건너뛰기
  if (strncmp(file_part, "static/", 7) == 0) {
    file_part += 7;  // "static/" 제거
  } else {
    return -1;  // "/static/" 프리픽스가 없음
  }

  // 3. 경로 안전성 검사
  if (!sf_is_safe_path(file_part)) {
    fprintf(stderr, "[SF] 경로 거부: %s (안전하지 않음)\n", file_part);
    return -1;
  }

  // 4. Dotfile 차단
  if (sf_is_dotfile(file_part)) {
    fprintf(stderr, "[SF] Dotfile 거부: %s\n", file_part);
    return -1;
  }

  // 5. 최종 경로 생성: root + "/" + file_part
  int n = snprintf(resolved_path, size, "%s/%s", root, file_part);
  if (n < 0 || (size_t)n >= size) {
    fprintf(stderr, "[SF] 경로 버퍼 오버플로우\n");
    return -1;
  }

  return 0;
}

/**
 * 파일 존재 및 크기 확인
 *
 * @param filepath: 파일 경로
 * @param out_size: 파일 크기 저장 (출력, NULL 가능)
 * @return: 0 (파일 존재), -1 (파일 없음 또는 에러)
 */
int sf_check_file(const char *filepath, off_t *out_size) {
  struct stat st;
  if (stat(filepath, &st) != 0) {
    return -1;
  }

  // 디렉토리이면 거부
  if (S_ISDIR(st.st_mode)) {
    return -1;
  }

  // 일반 파일이 아니면 거부 (심볼릭 링크, 소켓 등)
  if (!S_ISREG(st.st_mode)) {
    return -1;
  }

  if (out_size) {
    *out_size = st.st_size;
  }

  return 0;
}

/**
 * HTTP 응답 헤더 생성
 *
 * @param status_code: HTTP 상태 코드
 * @param mime_type: Content-Type
 * @param content_length: Content-Length
 * @param buffer: 헤더 저장 (출력)
 * @param size: 버퍼 크기
 * @return: 헤더 길이 (성공), -1 (실패)
 */
int sf_build_response_header(int status_code, const char *mime_type,
                              off_t content_length, char *buffer, size_t size) {
  if (!mime_type || !buffer) {
    return -1;
  }

  const char *status_text = "200 OK";
  if (status_code == 404) status_text = "404 Not Found";
  else if (status_code == 403) status_text = "403 Forbidden";
  else if (status_code == 500) status_text = "500 Internal Server Error";

  int n = snprintf(buffer, size,
    "HTTP/1.1 %d %s\r\n"
    "Content-Type: %s\r\n"
    "Content-Length: %lld\r\n"
    "Connection: keep-alive\r\n"
    "Cache-Control: max-age=3600\r\n"
    "\r\n",
    status_code, status_text, mime_type, (long long)content_length);

  if (n < 0 || (size_t)n >= size) {
    return -1;
  }

  return n;
}

/**
 * 404 응답 생성
 *
 * @param buffer: 응답 저장 (출력)
 * @param size: 버퍼 크기
 * @return: 응답 길이 (성공), -1 (실패)
 */
int sf_build_404_response(char *buffer, size_t size) {
  if (!buffer) {
    return -1;
  }

  const char *body = "404 Not Found";
  int n = snprintf(buffer, size,
    "HTTP/1.1 404 Not Found\r\n"
    "Content-Type: text/plain\r\n"
    "Content-Length: %zu\r\n"
    "Connection: keep-alive\r\n"
    "\r\n"
    "%s",
    strlen(body), body);

  if (n < 0 || (size_t)n >= size) {
    return -1;
  }

  return n;
}

/**
 * 403 (Forbidden) 응답 생성
 *
 * @param buffer: 응답 저장 (출력)
 * @param size: 버퍼 크기
 * @return: 응답 길이 (성공), -1 (실패)
 */
int sf_build_403_response(char *buffer, size_t size) {
  if (!buffer) {
    return -1;
  }

  const char *body = "403 Forbidden";
  int n = snprintf(buffer, size,
    "HTTP/1.1 403 Forbidden\r\n"
    "Content-Type: text/plain\r\n"
    "Content-Length: %zu\r\n"
    "Connection: keep-alive\r\n"
    "\r\n"
    "%s",
    strlen(body), body);

  if (n < 0 || (size_t)n >= size) {
    return -1;
  }

  return n;
}

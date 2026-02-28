"""
벡터 DB 검색 REST API 서버
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import sys
from pathlib import Path

# Add search module
sys.path.insert(0, str(Path(__file__).parent))
from vector_db import VectorDB

# Load database
DB_PATH = Path(__file__).parent.parent.parent / "LANGUAGE_VECTORS_COMPLETE.jsonl"
db = VectorDB(str(DB_PATH))

class SearchAPIHandler(BaseHTTPRequestHandler):
    """검색 API 핸들러"""
    
    def do_GET(self):
        """GET 요청 처리"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        response = None
        status = 404
        
        try:
            # Health check
            if path == "/health":
                response = {
                    "status": "healthy",
                    "total_languages": len(db.languages),
                    "total_capabilities": db.get_statistics()['total_capabilities'],
                    "total_constraints": db.get_statistics()['total_constraints']
                }
                status = 200
            
            # List all languages
            elif path == "/languages":
                all_langs = db.get_all_languages()
                response = {
                    "total": len(all_langs),
                    "languages": sorted(all_langs.keys())
                }
                status = 200
            
            # Search by name
            elif path == "/search/name":
                query = query_params.get('q', [''])[0]
                limit = int(query_params.get('limit', ['10'])[0])
                
                if not query:
                    response = {"error": "Parameter 'q' is required"}
                    status = 400
                else:
                    results = db.search_by_name(query, limit)
                    response = {
                        "query": query,
                        "count": len(results),
                        "results": results
                    }
                    status = 200
            
            # Search by capability
            elif path == "/search/capability":
                capability = query_params.get('capability', [''])[0]
                limit = int(query_params.get('limit', ['10'])[0])
                
                if not capability:
                    response = {"error": "Parameter 'capability' is required"}
                    status = 400
                else:
                    results = db.search_by_capability(capability, limit)
                    response = {
                        "capability": capability,
                        "count": len(results),
                        "results": results
                    }
                    status = 200
            
            # Search by constraint
            elif path == "/search/constraint":
                key = query_params.get('key', [''])[0]
                value = query_params.get('value', [''])[0]
                limit = int(query_params.get('limit', ['10'])[0])
                
                if not key or not value:
                    response = {"error": "Parameters 'key' and 'value' are required"}
                    status = 400
                else:
                    results = db.search_by_constraint(key, value, limit)
                    response = {
                        "constraint": f"{key}={value}",
                        "count": len(results),
                        "results": results
                    }
                    status = 200
            
            # Get language info
            elif path.startswith("/language/"):
                lang_name = path.split("/language/")[1]
                info = db.get_language_info(lang_name)
                
                if not info:
                    response = {"error": f"Language '{lang_name}' not found"}
                    status = 404
                else:
                    response = info
                    status = 200
            
            # Recommend languages
            elif path == "/recommend":
                capabilities = query_params.get('capabilities', [])
                limit = int(query_params.get('limit', ['5'])[0])
                
                results = db.recommend_by_requirements(capabilities, limit)
                response = {
                    "capabilities": capabilities,
                    "count": len(results),
                    "recommendations": results
                }
                status = 200
            
            # Statistics
            elif path == "/stats":
                stats = db.get_statistics()
                response = stats
                status = 200
            
        except Exception as e:
            response = {"error": str(e)}
            status = 500
        
        # Send response
        if response:
            self.send_response(status)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        """CORS 지원"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """로그 포맷"""
        print(f"[{self.client_address[0]}] {format % args}")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 35100
    
    server = HTTPServer(('0.0.0.0', port), SearchAPIHandler)
    print(f"🚀 벡터 DB 검색 API 서버 시작")
    print(f"   주소: http://0.0.0.0:{port}")
    print(f"   언어 수: {len(db.languages)}개")
    print(f"\n📡 엔드포인트:")
    print(f"   GET /health                    - 헬스 체크")
    print(f"   GET /languages                 - 모든 언어 목록")
    print(f"   GET /search/name?q=...         - 언어명 검색")
    print(f"   GET /search/capability?capability=... - 능력으로 검색")
    print(f"   GET /search/constraint?key=...&value=... - 제약으로 검색")
    print(f"   GET /language/{'{language}'}             - 언어 정보")
    print(f"   GET /recommend?capabilities=... - 추천")
    print(f"   GET /stats                     - 통계")
    print(f"\n⏰ 서버 시작...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️  서버 종료")
        server.server_close()

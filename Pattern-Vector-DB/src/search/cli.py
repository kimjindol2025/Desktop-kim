"""
벡터 DB 검색 CLI 인터페이스
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vector_db import VectorDB

def print_header(title):
    """헤더 출력"""
    print(f"\n{'='*70}")
    print(f"🔍 {title}")
    print(f"{'='*70}")

def print_table(headers, rows):
    """테이블 출력"""
    col_widths = [max(len(h), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    
    # 헤더
    print("  ".join(h.ljust(w) for h, w in zip(headers, col_widths)))
    print("  ".join("-" * w for w in col_widths))
    
    # 데이터
    for row in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(row, col_widths)))

def search_by_name(db, query):
    """언어명 검색"""
    print_header(f"언어명 검색: '{query}'")
    results = db.search_by_name(query, limit=10)
    
    if results:
        for i, lang in enumerate(results, 1):
            print(f"  {i}. {lang}")
    else:
        print("  검색 결과 없음")

def search_by_capability(db, capability):
    """능력으로 검색"""
    print_header(f"능력으로 검색: '{capability}'")
    results = db.search_by_capability(capability, limit=10)
    
    if results:
        for i, lang in enumerate(results, 1):
            print(f"  {i}. {lang}")
    else:
        print("  검색 결과 없음")

def get_language_info(db, language):
    """언어 정보"""
    print_header(f"언어 정보: {language}")
    info = db.get_language_info(language)
    
    if not info:
        print(f"  ❌ 언어 '{language}'를 찾을 수 없음")
        return
    
    print(f"\n📌 {info['language']}")
    print(f"   벡터: {info['vector_count']}개")
    
    print(f"\n✅ 능력 ({len(info['capabilities'])}개):")
    for cap in info['capabilities']:
        print(f"   • {cap}")
    
    if info['constraints']:
        print(f"\n⚠️  제약:")
        for constraint in info['constraints']:
            forbidden = constraint.get('forbidden_when', {})
            print(f"   • 금지: {dict(forbidden)}")
            print(f"     심각도: {constraint.get('severity')}")
            print(f"     대안: {', '.join(constraint.get('alternatives', []))}")

def list_all_languages(db):
    """모든 언어 목록"""
    print_header("모든 언어 목록")
    langs = sorted(db.get_all_languages().items())
    
    rows = [(i, lang, cap_count) for i, (lang, cap_count) in enumerate(langs, 1)]
    print_table(["#", "언어", "능력"], rows)
    print(f"\n총 {len(langs)}개 언어")

def recommend(db, capabilities):
    """추천"""
    print_header(f"능력 기반 추천: {capabilities}")
    results = db.recommend_by_requirements(capabilities, limit=5)
    
    if results:
        rows = [
            (i, r['language'], r['score'], r['total_capabilities'])
            for i, r in enumerate(results, 1)
        ]
        print_table(["순위", "언어", "점수", "전체능력"], rows)
    else:
        print("  추천 결과 없음")

def show_statistics(db):
    """통계"""
    print_header("통계")
    stats = db.get_statistics()
    
    print(f"  총 언어: {stats['total_languages']}개")
    print(f"  총 능력: {stats['total_capabilities']}개")
    print(f"  총 제약: {stats['total_constraints']}개")
    print(f"  평균 능력/언어: {stats['avg_capabilities_per_language']:.1f}개")

def show_help():
    """도움말"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║              벡터 DB 검색 CLI                                     ║
╚════════════════════════════════════════════════════════════════════╝

명령어:
  search name <query>              - 언어명 검색 (예: python)
  search capability <name>          - 능력으로 검색 (예: web_client_runtime)
  info <language>                   - 언어 정보 조회 (예: Rust)
  list                              - 모든 언어 목록
  recommend <cap1> <cap2> ...       - 능력 기반 추천
  stats                             - 통계
  help                              - 도움말
  quit                              - 종료

예시:
  > search name python
  > search capability web_client_runtime
  > info Rust
  > recommend web_client_runtime asynchronous_programming
  > stats

""")

def main():
    """메인 인터페이스"""
    db_path = Path(__file__).parent.parent.parent / "LANGUAGE_VECTORS_COMPLETE.jsonl"
    
    if not db_path.exists():
        print(f"❌ 파일을 찾을 수 없음: {db_path}")
        return
    
    print("📚 벡터 DB 로드 중...")
    db = VectorDB(str(db_path))
    print(f"✅ {len(db.languages)}개 언어 로드 완료\n")
    
    print("💡 'help'를 입력하면 도움말을 볼 수 있습니다.")
    print("🚀 시작하세요!\n")
    
    while True:
        try:
            cmd = input("🔍 > ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            if command == "quit" or command == "exit":
                print("👋 종료합니다")
                break
            
            elif command == "help":
                show_help()
            
            elif command == "search":
                if len(args) < 2:
                    print("❌ 사용법: search <type> <query>")
                    print("   타입: name, capability")
                else:
                    search_type = args[0].lower()
                    query = " ".join(args[1:])
                    
                    if search_type == "name":
                        search_by_name(db, query)
                    elif search_type == "capability":
                        search_by_capability(db, query)
                    else:
                        print(f"❌ 알 수 없는 검색 타입: {search_type}")
            
            elif command == "info":
                if not args:
                    print("❌ 사용법: info <language>")
                else:
                    get_language_info(db, args[0])
            
            elif command == "list":
                list_all_languages(db)
            
            elif command == "recommend":
                if not args:
                    print("❌ 사용법: recommend <capability1> [capability2] ...")
                else:
                    recommend(db, args)
            
            elif command == "stats":
                show_statistics(db)
            
            else:
                print(f"❌ 알 수 없는 명령어: {command}")
                print("💡 'help'를 입력하면 도움말을 볼 수 있습니다.")
        
        except KeyboardInterrupt:
            print("\n\n👋 종료합니다")
            break
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == "__main__":
    main()

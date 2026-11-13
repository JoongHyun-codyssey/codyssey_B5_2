"""Mini Git 실행 파일.

실행: python main.py

파일 구성
  main.py           : REPL (입력 -> 실행 -> 출력 반복)
  cli.py            : 명령어 파싱과 출력
  repository.py     : 커밋 노드, 저장소, 브랜치
  algorithms.py     : 병합 정렬 / 위상 정렬 / 최단 경로 / 조상 탐색
  inverted_index.py : 역색인
"""

from cli import MiniGit


def main():
    """exit/quit 를 입력할 때까지 명령을 받아 실행한다."""
    mini_git = MiniGit()
    
    while True:
        try:
            line = input("mini-git> ")
        except EOFError:
            break

        if line.strip().lower() in ("exit", "quit"):
            break
        output = mini_git.execute(line)
        if output:
            print(output)
        
        print()


if __name__ == "__main__":
    main()

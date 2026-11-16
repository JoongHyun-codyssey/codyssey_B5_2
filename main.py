"""
Mini Git

실행하는 법:  python main.py
"""

import hashlib
import shlex
from datetime import datetime


class MiniGitError(Exception):
    """잘못된 입력에 대한 에러. 에러 메시지가 그대로 화면에 출력된다."""


# =====================================================================
# 1장. 커밋
# =====================================================================

class Commit:
    """커밋 그래프의 노드. 한 번 만들면 내용을 바꾸지 않는다."""

    def __init__(self, commit_hash, message, author, timestamp, parents, branch):
        self.hash = commit_hash    # 커밋 식별자 (예: "2edb318")
        self.message = message     # 커밋 메시지
        self.author = author       # 작성자
        self.timestamp = timestamp # 커밋 생성 시각
        self.parents = parents     # 부모 커밋의 hash 목록 (0개 이상)
        self.branch = branch       # 커밋을 만들 때의 브랜치 이름 (출력용)


class HashGenerator:
    """세션 전체에서 중복되지 않는 7자리 커밋 hash 를 만든다.

    "카운터:작성자:메시지" 문자열의 SHA-1 해시값에서 앞 7자리를 사용한다.
    이미 사용한 hash 와 같으면 카운터를 증가시켜 다시 만든다.
    """

    def __init__(self):
        self.counter = 0
        self.used_hashes = set()  # 지금까지 사용한 hash

    def generate(self, author, message):
        while True:
            self.counter += 1
            text = f"{self.counter}:{author}:{message}"
            new_hash = hashlib.sha1(text.encode()).hexdigest()[:7]
            if new_hash not in self.used_hashes:
                self.used_hashes.add(new_hash)
                return new_hash


# =====================================================================
# 2장. 역색인
# =====================================================================

def tokenize(text):
    """문자열을 키워드 목록으로 바꾼다. 예: 'Add Login login' -> ['add', 'login']

    공백 기준으로 분리하고, 소문자로 정규화하고, 중복 단어는 제거한다.
    """
    tokens = []
    for token in text.lower().split():
        if token not in tokens:
            tokens.append(token)
    return tokens


class InvertedIndex:
    """역색인(Inverted Index): 키워드 / 작성자 -> 커밋 hash 목록.

    커밋을 만들 때마다 색인을 갱신해 두고, 검색할 때는 모든 커밋을
    순회(O(N))하지 않고 딕셔너리 조회(평균 O(1))로 후보를 바로 가져온다.

      keyword_index = {"login": ["2edb318"], "add": ["2edb318", "3ef0563"], ...}
      author_index  = {"Alice": ["ffefc7d", "2edb318", "3ef0563"]}
    """

    def __init__(self):
        self.keyword_index = {}  # 키워드 -> 커밋 hash 목록
        self.author_index = {}   # 작성자 -> 커밋 hash 목록

    def add(self, commit):
        """커밋의 메시지 키워드와 작성자를 색인에 등록한다."""
        for keyword in tokenize(commit.message):
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            self.keyword_index[keyword].append(commit.hash)

        if commit.author not in self.author_index:
            self.author_index[commit.author] = []
        self.author_index[commit.author].append(commit.hash)

    def search_keyword(self, query):
        """query 의 모든 키워드가 메시지에 포함된 커밋의 hash 목록을 반환한다."""
        keywords = tokenize(query)
        if len(keywords) == 0:
            return []

        # 첫 번째 키워드의 후보 목록에서 시작한다.
        result = self.keyword_index.get(keywords[0], [])

        # 나머지 키워드를 포함하지 않는 커밋을 후보에서 제외한다 (교집합).
        for keyword in keywords[1:]:
            matching = set(self.keyword_index.get(keyword, []))
            intersection = []
            for commit_hash in result:
                if commit_hash in matching:
                    intersection.append(commit_hash)
            result = intersection

        return list(result)

    def search_author(self, author):
        """해당 작성자의 커밋 hash 목록을 반환한다. (이름은 대소문자를 구분한다)"""
        return list(self.author_index.get(author, []))


# =====================================================================
# 3장. 저장소
# =====================================================================

class Repository:
    """커밋 그래프와 브랜치를 관리하는 저장소.

    새 커밋은 이미 존재하는 커밋만 부모로 가질 수 있다. 따라서 간선은 항상
    과거의 커밋을 향하고, 간선을 따라가서 출발한 커밋으로 돌아오는 사이클이
    생기지 않는다. 그래서 커밋 그래프는 항상 DAG(방향성 비순환 그래프)이다.
    """

    def __init__(self, author, hash_generator):
        self.author = author
        self.commits = {}                # hash -> 커밋 (해시맵, 평균 O(1) 조회)
        self.children = {}               # hash -> 자식 커밋의 hash 목록
        self.branches = {"main": None}   # 브랜치 이름 -> 가리키는 커밋 hash (커밋이 없으면 None)
        self.head = "main"               # HEAD: 현재 브랜치 이름
        self.index = InvertedIndex()
        self.hash_generator = hash_generator

    def create_branch(self, name):
        """현재 커밋(HEAD)을 가리키는 새 브랜치를 만든다."""
        if name in self.branches:
            raise MiniGitError(f"Branch already exists: {name}")
        self.branches[name] = self.branches[self.head]

    def switch(self, name):
        """HEAD 를 지정한 브랜치로 이동한다."""
        if name not in self.branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self.head = name

    def commit(self, message):
        """현재 HEAD 를 부모로 하는 새 커밋을 만든다.

        1. 현재 브랜치가 가리키는 커밋을 부모로 정한다.
        2. 새 커밋을 저장하고, 부모의 자식 목록에 추가한다.
        3. 현재 브랜치가 새 커밋을 가리키도록 옮긴다.
        4. 역색인을 갱신한다.
        """
        parent = self.branches[self.head]
        if parent is None:
            parents = []          # 첫 커밋은 부모가 없다
        else:
            parents = [parent]

        new_commit = Commit(
            commit_hash=self.hash_generator.generate(self.author, message),
            message=message,
            author=self.author,
            timestamp=datetime.now(),
            parents=parents,
            branch=self.head,
        )

        self.commits[new_commit.hash] = new_commit
        self.children[new_commit.hash] = []
        for parent_hash in new_commit.parents:
            self.children[parent_hash].append(new_commit.hash)

        self.branches[self.head] = new_commit.hash
        self.index.add(new_commit)
        return new_commit

    def get_commit(self, commit_hash):
        """hash 로 커밋을 조회한다. 없는 hash 이면 에러를 발생시킨다."""
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]


# =====================================================================
# 4장. 정렬 (병합 정렬)
# =====================================================================
#
# sorted() 와 list.sort() 를 사용하지 않고 직접 구현한 병합 정렬이다.
#
#   1. 목록을 절반으로 나눈다. 원소가 1개가 될 때까지 반복한다.
#   2. 정렬된 두 목록의 맨 앞 원소끼리 비교하면서,
#      더 작은 원소를 먼저 꺼내 하나의 목록으로 합친다.
#
#   [4, 1, 3, 2] -> [4, 1] [3, 2] -> [4] [1] [3] [2]
#                -> [1, 4] [2, 3] -> [1, 2, 3, 4]
#
# - 시간복잡도: 평균과 최악 모두 O(n log n)
# - 안정 정렬: 값이 같은 원소는 원래 순서를 유지한다.

def sort_key(commit, sort_by):
    """정렬 기준에 따라 비교할 값을 반환한다. "date" 는 생성 시각, "author" 는 작성자 이름."""
    if sort_by == "date":
        return commit.timestamp
    return commit.author


def merge_sort(commits, sort_by):
    """커밋 목록을 sort_by 기준 오름차순으로 정렬한 새 목록을 반환한다."""
    if len(commits) <= 1:
        return list(commits)

    middle = len(commits) // 2
    left = merge_sort(commits[:middle], sort_by)
    right = merge_sort(commits[middle:], sort_by)
    return merge(left, right, sort_by)


def merge(left, right, sort_by):
    """정렬된 두 목록을 하나의 정렬된 목록으로 합친다."""
    merged = []
    i = 0  # left 에서 비교할 위치
    j = 0  # right 에서 비교할 위치

    while i < len(left) and j < len(right):
        # 값이 같으면 왼쪽 원소를 먼저 넣는다. 그래서 안정 정렬이 된다.
        if sort_key(left[i], sort_by) <= sort_key(right[j], sort_by):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    # 한쪽 목록이 끝나면 다른 쪽에 남은 원소를 그대로 뒤에 붙인다.
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


# =====================================================================
# 5장. 그래프 탐색
# =====================================================================
#
# 세 탐색 함수 모두 큐(먼저 넣은 것을 먼저 꺼내는 자료구조)를 사용한다.
# 큐는 리스트 queue 와 다음에 꺼낼 위치 front 로 구현한다.
# 앞에서 원소를 삭제하지 않고 front 만 옮기므로 꺼내는 비용이 O(1)이다.
# 시간복잡도는 모두 O(V + E)이다. (V: 커밋 수, E: 부모 연결 수)

def topological_sort(repo):
    """부모가 항상 자식보다 먼저 나오는 hash 순서를 반환한다. (위상 정렬, Kahn 알고리즘)

    아직 처리되지 않은 부모의 수(진입 차수)가 0인 커밋만 큐에 넣을 수 있다.
      1. 부모가 없는 커밋을 큐에 넣는다.
      2. 큐에서 커밋을 하나씩 꺼내, 그 자식들의 진입 차수를 1 줄인다.
      3. 진입 차수가 0이 된 자식을 큐에 넣는다.
    """
    in_degree = {}  # 커밋 hash -> 아직 처리되지 않은 부모 수
    for commit_hash, commit in repo.commits.items():
        in_degree[commit_hash] = len(commit.parents)

    queue = []
    for commit_hash in repo.commits:
        if in_degree[commit_hash] == 0:
            queue.append(commit_hash)

    front = 0
    while front < len(queue):
        current = queue[front]
        front += 1
        for child in repo.children[current]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    return queue  # 큐에 들어간 순서가 곧 출력 순서이다


def neighbors(repo, commit_hash):
    """부모와 자식을 모두 이웃으로 반환한다. (간선을 무방향으로 볼 때 사용)"""
    return repo.commits[commit_hash].parents + repo.children[commit_hash]


def bfs_distances(repo, start):
    """start 에서 각 커밋까지의 최소 간선 수를 구한다. (너비 우선 탐색, BFS)

    가까운 커밋부터 차례로 방문하므로, 처음 방문했을 때의 거리가 최단 거리이다.
    결과에 없는 커밋은 start 와 연결되어 있지 않은 커밋이다.
    """
    distance = {start: 0}
    queue = [start]
    front = 0
    while front < len(queue):
        current = queue[front]
        front += 1
        for neighbor in neighbors(repo, current):
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    return distance


def shortest_path(repo, start, goal):
    """start 에서 goal 까지의 최단 경로(간선 수 최소)를 반환한다. 경로가 없으면 None.

      1. goal 에서 BFS 를 수행해 모든 커밋의 'goal 까지 거리'를 구한다.
      2. start 에서 출발해 거리가 1 줄어드는 이웃으로 이동한다.
         그런 이웃이 여러 개면 hash 가 가장 작은 이웃을 선택한다.
         (hash 길이가 모두 같으므로, 경로를 "a->b->c" 문자열로 만들었을 때
          사전순으로 가장 작은 경로가 된다)
    """
    distance_to_goal = bfs_distances(repo, goal)
    if start not in distance_to_goal:
        return None  # start 와 goal 이 연결되어 있지 않다

    path = [start]
    current = start
    while current != goal:
        closer_neighbors = []
        for neighbor in neighbors(repo, current):
            if distance_to_goal[neighbor] == distance_to_goal[current] - 1:
                closer_neighbors.append(neighbor)
        current = min(closer_neighbors)
        path.append(current)

    return path


def find_ancestors(repo, start):
    """start 에서 부모 방향으로 도달 가능한 모든 조상의 hash 목록을 반환한다. (BFS)

    부모가 여러 개인 커밋이 있으면 같은 조상에 여러 경로로 도달할 수 있다.
    방문한 커밋을 집합(visited)에 기록해 각 조상을 한 번만 결과에 넣는다.
    """
    visited = set()
    ancestors = []
    queue = [start]
    front = 0
    while front < len(queue):
        current = queue[front]
        front += 1
        for parent in repo.commits[current].parents:
            if parent not in visited:
                visited.add(parent)
                ancestors.append(parent)
                queue.append(parent)
    return ancestors


# =====================================================================
# 6장. 명령어 처리
# =====================================================================

COMMANDS = ("init", "branch", "switch", "commit", "log", "path", "ancestors", "search")


def require_args(args, count):
    """인자 개수를 확인한다. 맞지 않으면 'Invalid args' 에러를 발생시킨다."""
    if len(args) != count:
        raise MiniGitError("Invalid args")


def format_commit(commit):
    """커밋 하나를 로그 출력 형식의 문자열로 바꾼다."""
    time_text = commit.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return (f"commit {commit.hash} ({commit.author}, {time_text}) [{commit.branch}]\n"
            f"    {commit.message}")


def format_commits(commits, empty_message):
    """커밋 목록을 출력 문자열로 바꾼다. 목록이 비어 있으면 empty_message 를 반환한다."""
    if len(commits) == 0:
        return empty_message
    lines = []
    for commit in commits:
        lines.append(format_commit(commit))
    return "\n".join(lines)


class MiniGit:
    """명령어 한 줄을 파싱해 실행하고, 출력할 문자열을 반환한다."""

    def __init__(self):
        self.repo = None  # INIT 전에는 저장소가 없다
        # HashGenerator 는 하나만 만들어 계속 사용한다.
        # INIT 으로 저장소를 새로 만들어도 이전에 사용한 hash 가 다시 나오지 않는다.
        self.hash_generator = HashGenerator()

    def execute(self, line):
        """명령어 한 줄을 실행하고 결과 문자열을 반환한다."""
        # shlex.split 은 따옴표로 감싼 인자를 하나의 토큰으로 분리한다.
        #   'commit "Add login"'  ->  ['commit', 'Add login']
        try:
            tokens = shlex.split(line)
        except ValueError:  # 따옴표를 닫지 않은 경우
            return "Invalid args"

        if len(tokens) == 0:
            return ""

        name = tokens[0].lower()  # 명령어는 대소문자를 구분하지 않는다
        args = tokens[1:]

        if name not in COMMANDS:
            return f"Unknown command: {tokens[0]}"
        if self.repo is None and name != "init":
            return "Not initialized. Run: INIT <user_name>"

        try:
            if name == "init":
                return self.cmd_init(args)
            if name == "branch":
                return self.cmd_branch(args)
            if name == "switch":
                return self.cmd_switch(args)
            if name == "commit":
                return self.cmd_commit(args)
            if name == "log":
                return self.cmd_log(args)
            if name == "path":
                return self.cmd_path(args)
            if name == "ancestors":
                return self.cmd_ancestors(args)
            return self.cmd_search(args)
        except MiniGitError as error:
            return str(error)

    def cmd_init(self, args):
        """INIT <user_name>: 저장소를 초기화하고 사용자를 설정한다."""
        require_args(args, 1)
        self.repo = Repository(args[0], self.hash_generator)
        return ("Initialized repository.\n"
                f"Current branch: {self.repo.head}\n"
                f"Current user: {self.repo.author}")

    def cmd_branch(self, args):
        """BRANCH <branch_name>: 현재 커밋을 가리키는 브랜치를 만든다."""
        require_args(args, 1)
        self.repo.create_branch(args[0])
        return f"Created branch: {args[0]}"

    def cmd_switch(self, args):
        """SWITCH <branch_name>: HEAD 를 해당 브랜치로 이동한다."""
        require_args(args, 1)
        self.repo.switch(args[0])
        return f"Switched to branch: {args[0]}"

    def cmd_commit(self, args):
        """COMMIT <message>: 현재 HEAD 를 부모로 하는 커밋을 만든다."""
        require_args(args, 1)
        commit = self.repo.commit(args[0])
        return f"[{commit.branch} {commit.hash}] {commit.message}"

    def cmd_log(self, args):
        """LOG: 부모 우선 순서로 출력한다. LOG --sort-by=date|author: 정렬해서 출력한다."""
        # 옵션이 없으면 위상 정렬 순서로 출력한다.
        if len(args) == 0:
            commits = []
            for commit_hash in topological_sort(self.repo):
                commits.append(self.repo.commits[commit_hash])
            return format_commits(commits, "No commits")

        # --sort-by=date 또는 --sort-by=author
        require_args(args, 1)
        option = args[0].lower()
        if option == "--sort-by=date":
            sort_by = "date"
        elif option == "--sort-by=author":
            sort_by = "author"
        else:
            raise MiniGitError("Invalid args")

        all_commits = list(self.repo.commits.values())
        return format_commits(merge_sort(all_commits, sort_by), "No commits")

    def cmd_path(self, args):
        """PATH <commit1> <commit2>: 두 커밋 사이의 최단 경로를 출력한다."""
        require_args(args, 2)
        start = self.repo.get_commit(args[0])
        goal = self.repo.get_commit(args[1])

        path = shortest_path(self.repo, start.hash, goal.hash)
        if path is None:
            return "No path"
        return "Path: " + " -> ".join(path)

    def cmd_ancestors(self, args):
        """ANCESTORS <commit_hash>: 해당 커밋의 모든 조상을 출력한다."""
        require_args(args, 1)
        commit = self.repo.get_commit(args[0])

        ancestors = []
        for commit_hash in find_ancestors(self.repo, commit.hash):
            ancestors.append(self.repo.commits[commit_hash])
        return format_commits(ancestors, "No ancestors")

    def cmd_search(self, args):
        """SEARCH <keyword> 또는 SEARCH --author=<name>: 역색인으로 커밋을 검색한다."""
        require_args(args, 1)
        query = args[0]

        # --author=<name> 이면 작성자로 검색한다.
        if query.lower().startswith("--author="):
            author = query[len("--author="):]
            if author == "":
                raise MiniGitError("Invalid args")
            hashes = self.repo.index.search_author(author)
        # 그 외에는 커밋 메시지의 키워드로 검색한다.
        else:
            hashes = self.repo.index.search_keyword(query)

        lines = [f"Found {len(hashes)} commit(s):"]
        for commit_hash in hashes:
            lines.append(f"- {commit_hash}: {self.repo.commits[commit_hash].message}")
        return "\n".join(lines)


# =====================================================================
# 7장. 프로그램 시작
# =====================================================================

def main():
    """REPL: 명령어 입력 -> 실행 -> 결과 출력을 반복한다.
    exit 또는 quit 를 입력하면 종료한다."""
    mini_git = MiniGit()
    while True:
        try:
            line = input("mini-git> ")
        except EOFError:  # 더 읽을 입력이 없는 경우
            break

        if line.strip().lower() in ("exit", "quit"):
            break

        output = mini_git.execute(line)
        if output != "":
            print(output)
        print()


if __name__ == "__main__":
    main()

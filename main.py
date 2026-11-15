"""
Mini Git (쉽게 읽는 버전)

실행하는 법:  python main.py

이 프로그램은 게임의 "세이브 포인트"를 기록하는 공책이에요.

  커밋(commit)   = 세이브 포인트 하나
  부모(parent)   = 바로 전에 만든 세이브 포인트
  브랜치(branch) = 세이브 포인트에 붙이는 이름표
  HEAD           = 지금 내가 쓰고 있는 이름표

책처럼 위에서부터 차례대로 읽으면 돼요.

  1장. 세이브 포인트(커밋)
  2장. 찾아보기(역색인)
  3장. 저장소
  4장. 줄 세우기(정렬)
  5장. 길 찾기(탐색)
  6장. 명령어 알아듣기
  7장. 프로그램 시작
"""

import hashlib
import shlex
from datetime import datetime


class MiniGitError(Exception):
    """사용자가 잘못 입력했을 때 쓰는 에러예요. 에러 메시지가 그대로 화면에 나와요."""


# =====================================================================
# 1장. 세이브 포인트(커밋)
# =====================================================================

class Commit:
    """세이브 포인트 하나. 한 번 만들면 내용을 바꾸지 않아요."""

    def __init__(self, commit_hash, message, author, timestamp, parents, branch):
        self.hash = commit_hash    # 번호 (예: "2edb318")
        self.message = message     # 무엇을 했는지 적은 메모
        self.author = author       # 만든 사람
        self.timestamp = timestamp # 만든 시각
        self.parents = parents     # 바로 전 세이브 포인트들의 번호 목록
        self.branch = branch       # 만들 때 쓰던 이름표


class HashMaker:
    """커밋마다 겹치지 않는 7글자 번호를 만들어요.

    만드는 방법:
      "몇 번째:누가:메모" 라는 글자를 SHA-1 이라는 '지문 기계'에 넣으면
      긴 지문이 나와요. 그중 앞 7글자만 번호로 써요.
      혹시 전에 나온 번호와 같으면, 몇 번째를 하나 올려서 다시 만들어요.
    """

    def __init__(self):
        self.count = 0
        self.used = set()  # 지금까지 나눠 준 번호들

    def make(self, author, message):
        while True:
            self.count += 1
            text = f"{self.count}:{author}:{message}"
            new_hash = hashlib.sha1(text.encode()).hexdigest()[:7]
            if new_hash not in self.used:
                self.used.add(new_hash)
                return new_hash


# =====================================================================
# 2장. 찾아보기(역색인)
# =====================================================================

def split_into_words(text):
    """'Add Login login' -> ['add', 'login']

    공백으로 자르고, 모두 소문자로 바꾸고, 같은 단어는 한 번만 남겨요.
    """
    words = []
    for word in text.lower().split():
        if word not in words:
            words.append(word)
    return words


class SearchBook:
    """책 맨 뒤에 있는 '찾아보기'와 같아요.

    책을 처음부터 끝까지 넘기지 않아도, 찾아보기에서 단어를 찾으면
    몇 쪽에 있는지 바로 알 수 있죠. 여기서는 커밋을 만들 때마다
    '단어 -> 그 단어가 들어간 커밋 번호들'을 미리 적어 둬요.

      words   = {"login": ["2edb318"], "add": ["2edb318", "3ef0563"], ...}
      authors = {"Alice": ["ffefc7d", "2edb318", "3ef0563"]}
    """

    def __init__(self):
        self.words = {}    # 단어 -> 커밋 번호 목록
        self.authors = {}  # 만든 사람 -> 커밋 번호 목록

    def add(self, commit):
        for word in split_into_words(commit.message):
            if word not in self.words:
                self.words[word] = []
            self.words[word].append(commit.hash)

        if commit.author not in self.authors:
            self.authors[commit.author] = []
        self.authors[commit.author].append(commit.hash)

    def find_by_words(self, text):
        """적은 단어가 '모두' 들어 있는 커밋 번호들을 돌려줘요."""
        words = split_into_words(text)
        if len(words) == 0:
            return []

        # 첫 단어가 들어간 커밋들에서 시작해서,
        found = self.words.get(words[0], [])

        # 다음 단어가 없는 커밋은 하나씩 빼요.
        for word in words[1:]:
            has_this_word = set(self.words.get(word, []))
            still_found = []
            for commit_hash in found:
                if commit_hash in has_this_word:
                    still_found.append(commit_hash)
            found = still_found

        return list(found)

    def find_by_author(self, author):
        """그 사람이 만든 커밋 번호들 (이름의 대문자/소문자를 구분해요)."""
        return list(self.authors.get(author, []))


# =====================================================================
# 3장. 저장소
# =====================================================================

class Repository:
    """세이브 포인트와 이름표를 모두 적어 두는 공책이에요.

    왜 커밋은 '빙글빙글 도는 길'(사이클)을 만들 수 없을까요?
      새 커밋은 '이미 있는' 커밋만 부모로 가질 수 있어요.
      그래서 화살표는 언제나 과거 쪽으로만 가요.
      과거로만 가면 출발한 곳으로 다시 돌아올 수 없죠.
      이런 그래프를 DAG(방향은 있고, 도는 길은 없는 그래프)라고 해요.
    """

    def __init__(self, author, hash_maker):
        self.author = author
        self.commits = {}                # 번호 -> 커밋 (번호만 알면 바로 꺼내요)
        self.children = {}               # 번호 -> 자식 커밋 번호 목록
        self.branches = {"main": None}   # 이름표 -> 붙어 있는 커밋 번호 (아직 없으면 None)
        self.current_branch = "main"     # HEAD: 지금 쓰고 있는 이름표
        self.search_book = SearchBook()
        self.hash_maker = hash_maker

    def make_branch(self, name):
        """지금 이름표가 붙은 커밋에 새 이름표를 하나 더 붙여요."""
        if name in self.branches:
            raise MiniGitError(f"Branch already exists: {name}")
        self.branches[name] = self.branches[self.current_branch]

    def switch_branch(self, name):
        """다른 이름표로 갈아타요."""
        if name not in self.branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self.current_branch = name

    def make_commit(self, message):
        """새 세이브 포인트를 만들어요.

        1. 지금 이름표가 붙은 커밋을 부모로 삼아요.
        2. 새 커밋을 공책에 적고, 부모의 자식 목록에도 적어요.
        3. 이름표를 새 커밋으로 옮겨 붙여요.
        4. 찾아보기에도 적어요.
        """
        parent = self.branches[self.current_branch]
        if parent is None:
            parents = []          # 첫 커밋은 부모가 없어요
        else:
            parents = [parent]

        commit = Commit(
            commit_hash=self.hash_maker.make(self.author, message),
            message=message,
            author=self.author,
            timestamp=datetime.now(),
            parents=parents,
            branch=self.current_branch,
        )

        self.commits[commit.hash] = commit
        self.children[commit.hash] = []
        for parent_hash in commit.parents:
            self.children[parent_hash].append(commit.hash)

        self.branches[self.current_branch] = commit.hash
        self.search_book.add(commit)
        return commit

    def get_commit(self, commit_hash):
        """번호로 커밋을 꺼내요. 없는 번호면 에러."""
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]


# =====================================================================
# 4장. 줄 세우기(정렬) - 병합 정렬
# =====================================================================
#
# 섞인 카드 더미를 정리하는 방법이에요.
#
#   1. 더미를 반으로 나눠요. 카드가 1장이 될 때까지 계속 나눠요.
#   2. 정리된 작은 더미 두 개를 맨 위 카드끼리 비교하면서,
#      더 작은 카드를 먼저 내려놓아 하나로 합쳐요.
#
#   [4, 1, 3, 2] -> [4, 1] [3, 2] -> [4] [1] [3] [2]
#                -> [1, 4] [2, 3] -> [1, 2, 3, 4]
#
# - 카드가 n장이면 약 n x log(n) 번 일해요. (운이 나빠도 똑같아요)
# - 값이 같으면 원래 순서를 그대로 지켜요. 이것을 '안정 정렬'이라고 해요.

def sort_value(commit, sort_by):
    """무엇을 기준으로 비교할지 골라요. "date" 면 시각, "author" 면 이름."""
    if sort_by == "date":
        return commit.timestamp
    return commit.author


def merge_sort(commits, sort_by):
    if len(commits) <= 1:
        return list(commits)

    middle = len(commits) // 2
    left = merge_sort(commits[:middle], sort_by)
    right = merge_sort(commits[middle:], sort_by)
    return merge(left, right, sort_by)


def merge(left, right, sort_by):
    """정리된 두 더미를 하나로 합쳐요."""
    result = []
    i = 0  # 왼쪽 더미에서 지금 보는 카드
    j = 0  # 오른쪽 더미에서 지금 보는 카드

    while i < len(left) and j < len(right):
        # 같으면 왼쪽을 먼저 놓아요. 그래서 원래 순서가 지켜져요.
        if sort_value(left[i], sort_by) <= sort_value(right[j], sort_by):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    # 한쪽이 다 떨어지면, 남은 카드는 그대로 뒤에 붙여요.
    result.extend(left[i:])
    result.extend(right[j:])
    return result


# =====================================================================
# 5장. 길 찾기(탐색)
# =====================================================================
#
# 세 함수 모두 '줄(line)'을 써요. 줄 맨 앞부터 한 명씩 처리하고,
# 새로 찾은 커밋은 줄 맨 뒤에 세워요. 그래서 가까운 것부터 차례로 처리돼요.

def parent_first_order(repo):
    """부모가 항상 자식보다 먼저 나오도록 줄을 세워요. (위상 정렬)

    규칙: '아직 줄에 서지 않은 부모'가 0명인 커밋만 줄에 설 수 있어요.
      1. 부모가 없는 커밋부터 줄에 세워요.
      2. 줄 앞에서부터 한 명씩 보면서, 그 커밋의 자식들에게
         "네 부모 한 명이 줄에 섰어" 하고 알려 줘요 (기다리는 수 - 1).
      3. 기다리는 부모가 0명이 된 자식은 줄 뒤에 서요.
    """
    waiting = {}  # 커밋 번호 -> 아직 줄에 서지 않은 부모 수
    for commit_hash, commit in repo.commits.items():
        waiting[commit_hash] = len(commit.parents)

    line = []
    for commit_hash in repo.commits:
        if waiting[commit_hash] == 0:
            line.append(commit_hash)

    position = 0
    while position < len(line):
        current = line[position]
        position += 1
        for child in repo.children[current]:
            waiting[child] -= 1
            if waiting[child] == 0:
                line.append(child)

    return line  # 줄 선 순서가 곧 출력 순서예요


def neighbors(repo, commit_hash):
    """부모와 자식 모두 '이웃'이에요. 길 찾기에서는 화살표 방향을 무시해요."""
    return repo.commits[commit_hash].parents + repo.children[commit_hash]


def count_steps_from(repo, start):
    """start 에서 각 커밋까지 몇 걸음인지 세요. (너비 우선 탐색, BFS)

    연못에 돌을 던지면 물결이 1칸, 2칸, 3칸... 퍼지죠?
    그것처럼 가까운 커밋부터 차례로 걸음 수를 적어요.
    물결이 닿지 않은 커밋은 연결되어 있지 않은 거예요.
    """
    steps = {start: 0}
    line = [start]
    position = 0
    while position < len(line):
        current = line[position]
        position += 1
        for neighbor in neighbors(repo, current):
            if neighbor not in steps:
                steps[neighbor] = steps[current] + 1
                line.append(neighbor)
    return steps


def find_shortest_path(repo, start, goal):
    """start 에서 goal 까지 가장 적은 걸음으로 가는 길. 길이 없으면 None.

      1. goal 에서 물결을 퍼뜨려 '도착까지 몇 걸음'을 적어요.
      2. start 에서 출발해서, 한 걸음 더 가까워지는 이웃으로 이동해요.
         그런 이웃이 여러 개면 번호가 가장 작은 쪽으로 가요.
         (그러면 길을 "a -> b -> c" 글자로 썼을 때 사전 순서로 가장 앞서는 길이 돼요)
    """
    steps_to_goal = count_steps_from(repo, goal)
    if start not in steps_to_goal:
        return None  # 물결이 start 까지 오지 못했어요

    path = [start]
    current = start
    while current != goal:
        one_step_closer = []
        for neighbor in neighbors(repo, current):
            if steps_to_goal[neighbor] == steps_to_goal[current] - 1:
                one_step_closer.append(neighbor)
        current = min(one_step_closer)
        path.append(current)

    return path


def find_ancestors(repo, start):
    """부모, 부모의 부모, ... 를 모두 찾아요. 족보를 거슬러 올라가는 것과 같아요.

    부모가 두 명인 커밋도 있을 수 있어서, 같은 조상을 두 번 만날 수 있어요.
    그래서 이미 찾은 커밋은 '찾았음(found)' 표시를 해서 한 번만 적어요.
    """
    found = set()
    ancestors = []
    line = [start]
    position = 0
    while position < len(line):
        current = line[position]
        position += 1
        for parent in repo.commits[current].parents:
            if parent not in found:
                found.add(parent)
                ancestors.append(parent)
                line.append(parent)
    return ancestors


# =====================================================================
# 6장. 명령어 알아듣기
# =====================================================================

ALL_COMMANDS = ("init", "branch", "switch", "commit", "log", "path", "ancestors", "search")


def need_args(args, count):
    """인자 개수가 맞는지 확인해요. 틀리면 'Invalid args'."""
    if len(args) != count:
        raise MiniGitError("Invalid args")


def commit_to_text(commit):
    """커밋 하나를 화면에 보여 줄 글자로 바꿔요."""
    time_text = commit.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return (f"commit {commit.hash} ({commit.author}, {time_text}) [{commit.branch}]\n"
            f"    {commit.message}")


def commits_to_text(commits, text_if_empty):
    if len(commits) == 0:
        return text_if_empty
    lines = []
    for commit in commits:
        lines.append(commit_to_text(commit))
    return "\n".join(lines)


class MiniGit:
    """명령어 한 줄을 받아서 실행하고, 화면에 보여 줄 글자를 돌려줘요."""

    def __init__(self):
        self.repo = None  # INIT 하기 전에는 공책이 없어요
        # 번호 기계는 하나만 만들어서 계속 써요.
        # 그래야 INIT 을 다시 해도 전에 나온 번호가 또 나오지 않아요.
        self.hash_maker = HashMaker()

    def run_command(self, line):
        # shlex.split 은 따옴표로 묶은 말을 한 덩어리로 잘라 줘요.
        #   'commit "Add login"'  ->  ['commit', 'Add login']
        try:
            words = shlex.split(line)
        except ValueError:  # 따옴표를 닫지 않았을 때
            return "Invalid args"

        if len(words) == 0:
            return ""

        name = words[0].lower()  # INIT, init, Init 모두 같은 명령으로 봐요
        args = words[1:]

        if name not in ALL_COMMANDS:
            return f"Unknown command: {words[0]}"
        if self.repo is None and name != "init":
            return "Not initialized. Run: INIT <user_name>"

        try:
            if name == "init":
                return self.init(args)
            if name == "branch":
                return self.branch(args)
            if name == "switch":
                return self.switch(args)
            if name == "commit":
                return self.commit(args)
            if name == "log":
                return self.log(args)
            if name == "path":
                return self.path(args)
            if name == "ancestors":
                return self.ancestors(args)
            return self.search(args)
        except MiniGitError as error:
            return str(error)

    def init(self, args):
        need_args(args, 1)
        self.repo = Repository(args[0], self.hash_maker)
        return ("Initialized repository.\n"
                f"Current branch: {self.repo.current_branch}\n"
                f"Current user: {self.repo.author}")

    def branch(self, args):
        need_args(args, 1)
        self.repo.make_branch(args[0])
        return f"Created branch: {args[0]}"

    def switch(self, args):
        need_args(args, 1)
        self.repo.switch_branch(args[0])
        return f"Switched to branch: {args[0]}"

    def commit(self, args):
        need_args(args, 1)
        commit = self.repo.make_commit(args[0])
        return f"[{commit.branch} {commit.hash}] {commit.message}"

    def log(self, args):
        # LOG 만 쓰면: 부모가 먼저 나오는 순서
        if len(args) == 0:
            commits = []
            for commit_hash in parent_first_order(self.repo):
                commits.append(self.repo.commits[commit_hash])
            return commits_to_text(commits, "No commits")

        # LOG --sort-by=date 또는 LOG --sort-by=author
        need_args(args, 1)
        option = args[0].lower()
        if option == "--sort-by=date":
            sort_by = "date"
        elif option == "--sort-by=author":
            sort_by = "author"
        else:
            raise MiniGitError("Invalid args")

        all_commits = list(self.repo.commits.values())
        return commits_to_text(merge_sort(all_commits, sort_by), "No commits")

    def path(self, args):
        need_args(args, 2)
        start = self.repo.get_commit(args[0])
        goal = self.repo.get_commit(args[1])

        path = find_shortest_path(self.repo, start.hash, goal.hash)
        if path is None:
            return "No path"
        return "Path: " + " -> ".join(path)

    def ancestors(self, args):
        need_args(args, 1)
        commit = self.repo.get_commit(args[0])

        ancestors = []
        for commit_hash in find_ancestors(self.repo, commit.hash):
            ancestors.append(self.repo.commits[commit_hash])
        return commits_to_text(ancestors, "No ancestors")

    def search(self, args):
        need_args(args, 1)
        text = args[0]

        # SEARCH --author=Alice  ->  만든 사람으로 찾기
        if text.lower().startswith("--author="):
            author = text[len("--author="):]
            if author == "":
                raise MiniGitError("Invalid args")
            found = self.repo.search_book.find_by_author(author)
        # SEARCH login  ->  메모 속 단어로 찾기
        else:
            found = self.repo.search_book.find_by_words(text)

        lines = [f"Found {len(found)} commit(s):"]
        for commit_hash in found:
            lines.append(f"- {commit_hash}: {self.repo.commits[commit_hash].message}")
        return "\n".join(lines)


# =====================================================================
# 7장. 프로그램 시작
# =====================================================================

def main():
    """명령어를 받고 -> 실행하고 -> 결과를 보여 주기를 계속 반복해요.
    exit 또는 quit 를 입력하면 끝나요."""
    mini_git = MiniGit()
    while True:
        try:
            line = input("mini-git> ")
        except EOFError:  # 더 읽을 입력이 없을 때
            break

        if line.strip().lower() in ("exit", "quit"):
            break

        result = mini_git.run_command(line)
        if result != "":
            print(result)
        print()


if __name__ == "__main__":
    main()

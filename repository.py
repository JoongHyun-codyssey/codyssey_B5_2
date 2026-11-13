"""커밋 노드(Commit)와 저장소(Repository)."""

import hashlib
import itertools
from dataclasses import dataclass
from datetime import datetime

from inverted_index import InvertedIndex


class MiniGitError(Exception):
    """사용자에게 그대로 보여 줄 에러 (예: Unknown branch: dev)."""


# hash 는 프로그램 실행(세션) 전체에서 유일해야 한다.
# INIT 을 다시 해도 겹치지 않도록 저장소 밖(모듈)에 둔다.
_hash_counter = itertools.count(1)
_used_hashes = set()


def new_hash(author, message):
    """증가 카운터를 섞어 7자리 hash 를 만든다. 이미 쓴 값이면 다시 만든다."""
    while True:
        text = f"{next(_hash_counter)}:{author}:{message}"
        candidate = hashlib.sha1(text.encode()).hexdigest()[:7]
        if candidate not in _used_hashes:
            _used_hashes.add(candidate)
            return candidate


@dataclass
class Commit:
    """커밋 그래프의 노드. parents 가 부모 커밋을 가리키는 간선이다."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: list  # 부모 커밋 hash 목록 (0개 이상)
    branch: str    # 커밋이 만들어진 브랜치 (출력용)


class Repository:
    """커밋 그래프와 브랜치를 관리한다.

    - commits  : hash -> Commit   (해시맵이라 hash 로 O(1) 조회)
    - children : hash -> 자식 hash 목록 (부모 -> 자식 방향 탐색용)
    - branches : 브랜치 이름 -> 가리키는 커밋 hash (커밋이 없으면 None)

    새 커밋은 이미 존재하는 커밋만 부모로 가질 수 있으므로 사이클이 생길 수
    없고, 그래서 그래프는 항상 DAG 이다.
    """

    def __init__(self, author):
        self.author = author
        self.commits = {}
        self.children = {}
        self.branches = {"main": None}
        self.head = "main"  # 현재 브랜치 이름
        self.index = InvertedIndex()

    def create_branch(self, name):
        """현재 커밋(HEAD)을 가리키는 새 브랜치를 만든다."""
        if name in self.branches:
            raise MiniGitError(f"Branch already exists: {name}")
        self.branches[name] = self.branches[self.head]

    def switch(self, name):
        """HEAD 를 지정한 브랜치로 옮긴다."""
        if name not in self.branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self.head = name

    def commit(self, message):
        """현재 HEAD 를 부모로 하는 커밋을 만들고 브랜치를 새 커밋으로 옮긴다."""
        parent = self.branches[self.head]
        new_commit = Commit(
            hash=new_hash(self.author, message),
            message=message,
            author=self.author,
            timestamp=datetime.now(),
            parents=[parent] if parent else [],
            branch=self.head,
        )
        self.commits[new_commit.hash] = new_commit
        self.children[new_commit.hash] = []
        for p in new_commit.parents:
            self.children[p].append(new_commit.hash)
        self.branches[self.head] = new_commit.hash
        self.index.add(new_commit)
        return new_commit

    def get(self, commit_hash):
        """hash 로 커밋을 찾는다. 없으면 에러."""
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]

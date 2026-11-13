"""명령어 처리: 한 줄을 파싱해 실행하고, 출력할 문자열을 돌려준다."""

import shlex

from algorithms import find_ancestors, merge_sort, shortest_path, topological_sort
from repository import MiniGitError, Repository

# LOG --sort-by=<기준> 에서 쓰는 비교 기준
SORT_KEYS = {
    "date": lambda commit: commit.timestamp,
    "author": lambda commit: commit.author,
}


def format_commit(commit):
    """커밋 하나를 로그 출력 형식으로 바꾼다."""
    time_text = commit.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return (f"commit {commit.hash} ({commit.author}, {time_text}) [{commit.branch}]\n"
            f"    {commit.message}")


def require_args(args, count):
    """인자 개수가 맞지 않으면 Invalid args."""
    if len(args) != count:
        raise MiniGitError("Invalid args")


class MiniGit:
    """명령어 이름 -> 처리 함수(cmd_*)로 연결해 실행한다."""

    def __init__(self):
        self.repo = None  # INIT 전에는 저장소가 없다
        self.commands = {
            "init": self.cmd_init,
            "branch": self.cmd_branch,
            "switch": self.cmd_switch,
            "commit": self.cmd_commit,
            "log": self.cmd_log,
            "path": self.cmd_path,
            "ancestors": self.cmd_ancestors,
            "search": self.cmd_search,
        }

    def execute(self, line):
        """명령어 한 줄을 실행하고 결과 문자열을 돌려준다."""
        try:
            tokens = shlex.split(line)  # 따옴표로 감싼 인자를 하나로 묶어 준다
        except ValueError:
            return "Invalid args"
        if not tokens:
            return ""

        name, args = tokens[0].lower(), tokens[1:]
        if name not in self.commands:
            return f"Unknown command: {tokens[0]}"
        if self.repo is None and name != "init":
            return "Not initialized. Run: INIT <user_name>"
        try:
            return self.commands[name](args)
        except MiniGitError as error:
            return str(error)

    def cmd_init(self, args):
        require_args(args, 1)
        self.repo = Repository(author=args[0])
        return ("Initialized repository.\n"
                f"Current branch: {self.repo.head}\n"
                f"Current user: {self.repo.author}")

    def cmd_branch(self, args):
        require_args(args, 1)
        self.repo.create_branch(args[0])
        return f"Created branch: {args[0]}"

    def cmd_switch(self, args):
        require_args(args, 1)
        self.repo.switch(args[0])
        return f"Switched to branch: {args[0]}"

    def cmd_commit(self, args):
        require_args(args, 1)
        commit = self.repo.commit(args[0])
        return f"[{commit.branch} {commit.hash}] {commit.message}"

    def cmd_log(self, args):
        repo = self.repo
        if not args:
            order = topological_sort(repo.commits, repo.children)
            commits = [repo.commits[h] for h in order]
        elif len(args) == 1 and args[0].lower().startswith("--sort-by="):
            sort_by = args[0].split("=", 1)[1].lower()
            if sort_by not in SORT_KEYS:
                raise MiniGitError("Invalid args")
            commits = merge_sort(list(repo.commits.values()), SORT_KEYS[sort_by])
        else:
            raise MiniGitError("Invalid args")

        if not commits:
            return "No commits"
        return "\n".join(format_commit(c) for c in commits)

    def cmd_path(self, args):
        require_args(args, 2)
        start, goal = self.repo.get(args[0]), self.repo.get(args[1])
        path = shortest_path(self.repo.commits, self.repo.children, start.hash, goal.hash)
        if path is None:
            return "No path"
        return "Path: " + " -> ".join(path)

    def cmd_ancestors(self, args):
        require_args(args, 1)
        commit = self.repo.get(args[0])
        ancestors = find_ancestors(self.repo.commits, commit.hash)
        if not ancestors:
            return "No ancestors"
        return "\n".join(format_commit(self.repo.commits[h]) for h in ancestors)

    def cmd_search(self, args):
        require_args(args, 1)
        query = args[0]
        if query.lower().startswith("--author="):
            name = query.split("=", 1)[1]
            if not name:
                raise MiniGitError("Invalid args")
            found = self.repo.index.search_author(name)
        else:
            found = self.repo.index.search_keyword(query)

        lines = [f"Found {len(found)} commit(s):"]
        lines += [f"- {h}: {self.repo.commits[h].message}" for h in found]
        return "\n".join(lines)

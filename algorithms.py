"""알고리즘 모음: 병합 정렬 / 위상 정렬 / 최단 경로(BFS) / 조상 탐색.

그래프 함수들은 두 개의 딕셔너리를 받는다.
  - commits  : hash -> Commit       (commit.parents 로 부모 방향 이동)
  - children : hash -> 자식 hash 목록 (자식 방향 이동)
"""

from collections import deque


def merge_sort(items, key):
    """병합 정렬. key(item) 값이 작은 순서로 정렬한 새 리스트를 돌려준다.

    - 시간복잡도: 평균/최악 모두 O(n log n)
    - 안정 정렬: 값이 같으면 원래 순서를 유지한다 (아래의 <= 비교 덕분).
    """
    if len(items) <= 1:
        return list(items)

    mid = len(items) // 2
    left = merge_sort(items[:mid], key)
    right = merge_sort(items[mid:], key)

    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):  # 같으면 왼쪽 먼저 -> 안정 정렬
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def topological_sort(commits, children):
    """위상 정렬(Kahn 알고리즘). 부모가 항상 자식보다 먼저 나오는 hash 목록.

    아직 출력되지 않은 부모의 수(진입 차수)가 0인 커밋부터 꺼내고,
    꺼낸 커밋의 자식들은 진입 차수를 1씩 줄인다. O(V + E)
    """
    remaining_parents = {h: len(c.parents) for h, c in commits.items()}
    queue = deque(h for h, count in remaining_parents.items() if count == 0)

    order = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for child in children[current]:
            remaining_parents[child] -= 1
            if remaining_parents[child] == 0:
                queue.append(child)
    return order


def shortest_path(commits, children, start, goal):
    """부모-자식 연결을 무방향 간선으로 본 최단 경로. 없으면 None. O(V + E)

    1) goal 에서 BFS 를 돌려 모든 커밋의 "goal 까지 거리"를 구한다.
    2) start 에서 출발해 거리가 1씩 줄어드는 이웃 중 hash 가 가장 작은 쪽으로
       이동한다. -> 최단 경로가 여러 개여도 사전순으로 가장 작은 경로가 된다.
    """
    def neighbors(commit_hash):
        return commits[commit_hash].parents + children[commit_hash]

    distance = {goal: 0}
    queue = deque([goal])
    while queue:
        current = queue.popleft()
        for nxt in neighbors(current):
            if nxt not in distance:
                distance[nxt] = distance[current] + 1
                queue.append(nxt)

    if start not in distance:
        return None

    path = [start]
    while path[-1] != goal:
        current = path[-1]
        closer = [n for n in neighbors(current) if distance[n] == distance[current] - 1]
        path.append(min(closer))
    return path


def find_ancestors(commits, start):
    """start 에서 부모 방향으로 도달 가능한 모든 조상 hash (BFS, 가까운 순)."""
    visited = {start}
    queue = deque([start])
    ancestors = []
    while queue:
        current = queue.popleft()
        for parent in commits[current].parents:
            if parent not in visited:
                visited.add(parent)
                ancestors.append(parent)
                queue.append(parent)
    return ancestors

"""그래프 계산(컴파일 시점 전용). 요청 처리 중에는 이 모듈을 쓰지 않는다.

모든 함수는 입력 순서와 무관하게 같은 결과를 내도록 정렬된 순서로 탐색한다.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

DEFINITE = "definite"
POSSIBLE = "possible"
_RANK = {DEFINITE: 0, POSSIBLE: 1}
_BY_RANK = {0: DEFINITE, 1: POSSIBLE}


def weaker(a: str, b: str) -> str:
    """경로상 certainty 결합: 하나라도 possible이면 possible."""
    return _BY_RANK[max(_RANK[a], _RANK[b])]


def find_cycle(nodes: Iterable[str], edges: Mapping[str, Sequence[str]]) -> list[str] | None:
    """방향 그래프의 순환 하나를 [a, b, ..., a] 형태로 돌려준다. 없으면 None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    for start in sorted(color):
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, list[str]]] = [(start, sorted(edges.get(start, ())))]
        path = [start]
        color[start] = GRAY
        while stack:
            node, pending = stack[-1]
            if not pending:
                color[node] = BLACK
                stack.pop()
                path.pop()
                continue
            nxt = pending.pop(0)
            state = color.get(nxt, BLACK)  # 존재하지 않는 대상은 참조 검증에서 따로 보고
            if state == GRAY:
                return path[path.index(nxt):] + [nxt]
            if state == WHITE:
                color[nxt] = GRAY
                path.append(nxt)
                stack.append((nxt, sorted(edges.get(nxt, ()))))
    return None


def ancestors(parents: Mapping[str, Sequence[str]]) -> dict[str, dict[str, int]]:
    """is_a 전이 폐포. {재료: {조상: 최소 depth}} (depth >= 1)."""
    result: dict[str, dict[str, int]] = {}
    for node in sorted(parents):
        found: dict[str, int] = {}
        frontier = [node]
        depth = 0
        while frontier:
            depth += 1
            nxt: list[str] = []
            for cur in frontier:
                for p in sorted(parents.get(cur, ())):
                    if p not in found and p != node:
                        found[p] = depth
                        nxt.append(p)
            frontier = nxt
        result[node] = found
    return result


@dataclass(frozen=True)
class Reach:
    certainty: str
    via: tuple[str, ...]  # 시작 재료부터 대상 재료까지의 id 경로


def expand_contains(
    nodes: Iterable[str],
    parents: Mapping[str, Sequence[str]],
    sources: Mapping[str, Sequence[tuple[str, str]]],
) -> dict[str, dict[str, Reach]]:
    """재료 x가 포함(가능)하는 재료 집합 (docs/plan.md 부록 C-3).

    이동 규칙:
      - 위로(is_a 부모): definite
      - 원천으로(derived_from): 엣지의 certainty
      - 아래로(is_a 자식): possible. 단, 마지막 원천 이동(또는 시작) 이후 위로 이동한 적이
        없을 때만 허용한다. 그래서 "젓갈류 → 새우젓 → 새우"는 따라가지만
        "새우 → 해산물 → 오징어"처럼 부모를 거쳐 형제로 내려가지는 않는다.
    경로 certainty는 경로상 최솟값이다. 대상마다 (certainty 강한 순, 경로 짧은 순, 경로 사전순)으로
    가장 좋은 경로 하나를 via로 기록한다. 상태 공간이 유한하고 certainty가 단조이므로 종료한다.
    """
    children: dict[str, list[str]] = {}
    for child, ps in parents.items():
        for p in ps:
            children.setdefault(p, []).append(child)
    for ps in children.values():
        ps.sort()

    result: dict[str, dict[str, Reach]] = {}
    for start in sorted(set(nodes)):
        best: dict[str, Reach] = {}
        seen: set[tuple[str, bool]] = set()
        heap: list[tuple[int, int, tuple[str, ...], str, bool]] = [(0, 1, (start,), start, True)]
        while heap:
            rank, length, path, node, can_descend = heapq.heappop(heap)
            if (node, can_descend) in seen:
                continue
            seen.add((node, can_descend))
            if node != start and node not in best:
                best[node] = Reach(_BY_RANK[rank], path)

            def push(nxt: str, step_rank: int, descend_after: bool) -> None:
                if (nxt, descend_after) in seen:
                    return
                heapq.heappush(
                    heap, (max(rank, step_rank), length + 1, path + (nxt,), nxt, descend_after)
                )

            for p in sorted(parents.get(node, ())):
                push(p, _RANK[DEFINITE], False)
            for src, cert in sorted(sources.get(node, ())):
                push(src, _RANK[cert], True)
            if can_descend:
                for c in children.get(node, ()):
                    push(c, _RANK[POSSIBLE], True)
        result[start] = best
    return result


def better(a: Reach, b: Reach) -> bool:
    """a가 b보다 강한 근거인가(certainty, 경로 길이, 경로 사전순)."""
    return (_RANK[a.certainty], len(a.via), a.via) < (_RANK[b.certainty], len(b.via), b.via)

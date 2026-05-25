from difflib import SequenceMatcher

from common.utils.strings import normalize_text

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None


def levenshtein_distance(first: str, second: str) -> int:
    first = normalize_text(first)
    second = normalize_text(second)
    if not first:
        return len(second)
    if not second:
        return len(first)
    rows = len(first) + 1
    cols = len(second) + 1
    matrix = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        matrix[i][0] = i
    for j in range(cols):
        matrix[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if first[i - 1] == second[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )
    return matrix[-1][-1]


def similarity_score(first: str, second: str) -> int:
    first = normalize_text(first)
    second = normalize_text(second)
    if not first or not second:
        return 0
    if fuzz:
        return int(fuzz.token_sort_ratio(first, second))
    return int(SequenceMatcher(None, first, second).ratio() * 100)

import json
import re
from pathlib import Path

_SOURCE_RE = re.compile(
    r"Chapter: (?P<chapter>.+?), paragraph number (?P<paragraph>\d+), "
    r"sentence number (?P<sentence>\d+) on page (?P<page>\S+)"
)


def load_sentences(path: Path) -> list[dict]:
    raw: list[dict] = json.loads(path.read_text())
    result = []
    for i, item in enumerate(raw):
        src = item.get('metadata', {}).get('source', '')
        m = _SOURCE_RE.search(src)
        result.append({
            'array_index': i,
            'page_content': item.get('page_content', ''),
            'chapter': m.group('chapter') if m else None,
            'paragraph': int(m.group('paragraph')) if m else None,
            'sentence': int(m.group('sentence')) if m else None,
            'page': m.group('page') if m else None,
        })
    return result


def get_chapters(sentences: list[dict]) -> list[str]:
    seen: list[str] = []
    for s in sentences:
        ch = s.get('chapter')
        if ch and ch not in seen:
            seen.append(ch)
    return seen


def find_by_position(
    sentences: list[dict], chapter: str, paragraph: int, sentence: int
) -> dict | None:
    ch_lower = chapter.lower()
    return next(
        (
            s for s in sentences
            if (s.get('chapter') or '').lower() == ch_lower
            and s.get('paragraph') == paragraph
            and s.get('sentence') == sentence
        ),
        None,
    )

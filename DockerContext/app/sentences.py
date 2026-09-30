import json
from pathlib import Path


def load_sentences(path: Path) -> list[dict]:
    raw: list[dict] = json.loads(path.read_text())
    result = []
    for i, item in enumerate(raw):
        meta = item.get('metadata', {})
        heading_chain = ' / '.join(
            meta[key] for key in ('h2', 'h3', 'h4', 'h5') if meta.get(key)
        )
        result.append({
            'array_index': i,
            'page_content': item.get('page_content', ''),
            'chapter': heading_chain or None,
            'paragraph': meta.get('paragraph_number'),
            'sentence': meta.get('sentence_number'),
            'page': meta.get('page'),
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

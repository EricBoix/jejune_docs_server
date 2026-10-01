import json
from pathlib import Path


def load_chunks(path: Path) -> list[dict]:
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


def get_chapters(chunks: list[dict]) -> list[str]:
    seen: list[str] = []
    for chunk in chunks:
        chapter = chunk.get('chapter')
        if chapter and chapter not in seen:
            seen.append(chapter)
    return seen


def find_chunk_by_position(
    chunks: list[dict], chapter: str, paragraph: int, sentence: int
) -> dict | None:
    chapter_lower = chapter.lower()
    return next(
        (
            chunk for chunk in chunks
            if (chunk.get('chapter') or '').lower() == chapter_lower
            and chunk.get('paragraph') == paragraph
            and chunk.get('sentence') == sentence
        ),
        None,
    )

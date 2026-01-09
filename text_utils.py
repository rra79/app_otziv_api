import re
import hashlib

CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")
_lang_cache = {}

def is_russian(text: str) -> bool:
    if not text:
        return False

    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if key in _lang_cache:
        return _lang_cache[key]

    result = bool(CYRILLIC_RE.search(text))
    _lang_cache[key] = result
    return result

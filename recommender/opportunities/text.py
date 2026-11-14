"""Bounded Korean field matching; not a general language understanding engine."""
import re
import unicodedata
from functools import lru_cache

# Recommendation-local aliases; shared catalog and API options are unchanged.
ROLE_ALIASES = {
    'software': ('웹 개발자', '앱 개발자', '개발자', '프로그래머', '소프트웨어 개발자', '백엔드', '백엔드 개발자',
                 '프론트엔드', '프론트엔드 개발자', 'backend', 'frontend',
                 '게임 개발', '게임개발', '게임 개발자', '게임개발자'),
    'ai': ('AI 엔지니어', '인공지능 엔지니어', 'AI 개발자', '인공지능 개발자'),
    'design': ('디자이너', '웹디자이너', '그래픽 디자이너'),
    'data': ('데이터 분석가', '데이터 사이언티스트', 'data analyst'),
}
PARTICLES = ('으로', '에서', '에게', '에는', '에도', '와는', '과는', '보다는',
             '의', '은', '는', '이', '가', '을', '를', '에', '로', '와', '과', '도', '만')
# Ambiguous negatives suppress scoring in their clause, including double negatives.
NEGATIVE = re.compile(
    r'않|싫|아니|아닌|아님|대신|보다는|말고|제외|원치|없|못|비희망|비선호|관심\s*무'
    r'|(?<!\w)안(?=\s)|(?<!\w)(?:not|no|without|avoid)(?!\w)')
CLAUSES = re.compile(r'[.!?;\n,]+|하지만|그러나|대신|보다는|말고|제외하고|아니라')


def normalized(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


@lru_cache(maxsize=256)
def phrase_pattern(phrase: str) -> re.Pattern:
    suffix = '|'.join(map(re.escape, PARTICLES))
    return re.compile(r'(?<!\w)' + re.escape(normalized(phrase)) + r'(?:' + suffix + r')?(?!\w)')


def contains_phrase(text: str, phrase: str) -> bool:
    return phrase_pattern(phrase).search(normalized(text)) is not None


def positive_mentions(text: str, aliases: list[str]) -> bool:
    # Keep exclusion markers on the left so “개발 말고 디자인” cannot score software.
    chunks = []
    offset = 0
    for match in CLAUSES.finditer(text):
        chunks.append(text[offset:match.end()])
        offset = match.end()
    chunks.append(text[offset:])
    return any(not NEGATIVE.search(normalized(chunk))
               and any(contains_phrase(chunk, alias) for alias in aliases)
               for chunk in chunks)


def field_matches(entries: list[str], code: str, aliases: list[str], *, free_text: bool) -> bool:
    names = [*aliases, *ROLE_ALIASES.get(code, ())]
    # The profile form accepts both “AI 관련 직무” and “ai관련 직무”.
    entries = [re.sub(r'(?<=\w)\s*관련(?=\s|$)', ' 관련', normalized(entry)) for entry in entries]
    if free_text:
        return any(positive_mentions(entry, names) for entry in entries)
    return any(re.sub(r'\s+관련(?:\s+(?:직무|분야))?$', '', entry) == normalized(name)
               for entry in entries for name in names)

# service/app/core/search.py
import re

class UnsafeRegexError(ValueError): ...

def safe_regex(pattern: str | None, flags=0, max_len=256):
    if not pattern:
        return None
    if len(pattern) > max_len:
        raise UnsafeRegexError("regex too long")
    # basic sanity checks against catastrophic backtracking
    if pattern.count("(") > 32 or any(x in pattern for x in ["(?R", "(?P>", "(?<=.*)"]):
        raise UnsafeRegexError("regex too complex")
    try:
        return re.compile(pattern, flags)
    except re.error as e:
        raise UnsafeRegexError(str(e))

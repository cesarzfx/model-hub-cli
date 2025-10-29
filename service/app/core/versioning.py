import re
from packaging.version import Version
from typing import Callable

def match_exact(v: str) -> Callable[[str], bool]:
    target = Version(v)
    return lambda s: Version(s) == target

def match_range(lo: str, hi: str) -> Callable[[str], bool]:
    lo_v, hi_v = Version(lo), Version(hi)
    return lambda s: lo_v <= Version(s) <= hi_v

def match_tilde(spec: str):
    # ~1.2.0  => >=1.2.0 <1.3.0
    v = Version(spec.replace("~", ""))
    upper = Version(f"{v.major}.{v.minor+1}.0")
    return lambda s: v <= Version(s) < upper

def match_caret(spec: str):
    # ^1.2.0 => >=1.2.0 <2.0.0 ; ^0.2.3 => >=0.2.3 <0.3.0
    v = Version(spec.replace("^", ""))
    upper = Version(f"{v.major+1}.0.0") if v.major > 0 else Version(f"0.{v.minor+1}.0")
    return lambda s: v <= Version(s) < upper

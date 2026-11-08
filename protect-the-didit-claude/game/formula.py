"""Safe formula parser for Bima's Graph path. No eval(): tokenizer -> recursive descent -> closures.

compile_formula(text, level) returns (f, pretty). f(x) -> float (may be nan / +-inf; callers treat those as holes).
Only whitelisted functions/constants exist; `x` is the only variable. Radians. Implicit multiplication (2x, 2(x+1),
x(x+1), 2sin(x), 3pi). Errors are FormulaError with a friendly message and a position.
"""
from __future__ import annotations

import math
import re

CONSTS = {"pi": math.pi, "e": math.e}


class FormulaError(Exception):
    def __init__(self, msg: str, pos: int = -1) -> None:
        super().__init__(msg)
        self.msg, self.pos = msg, pos


def _safe1(fn):
    def g(x):
        try:
            return fn(x)
        except ValueError:
            return math.nan
        except OverflowError:
            return math.inf
    return g


def _safe2(fn):
    def g(a, b):
        try:
            return fn(a, b)
        except (ValueError, OverflowError):
            return math.nan
    return g


# name -> (arity, function, level that unlocks it)
FUNCS = {
    "abs": (1, abs, 2), "sqrt": (1, _safe1(math.sqrt), 2), "min": (2, min, 2), "max": (2, max, 2),
    "sin": (1, _safe1(math.sin), 4), "cos": (1, _safe1(math.cos), 4), "tan": (1, _safe1(math.tan), 4),
    "asin": (1, _safe1(math.asin), 4), "acos": (1, _safe1(math.acos), 4), "atan": (1, _safe1(math.atan), 4),
    "ln": (1, _safe1(math.log), 4), "log": (1, _safe1(math.log10), 4), "exp": (1, _safe1(math.exp), 4),
}


def _div(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return math.copysign(math.inf, a) if a else math.nan


def _pow(a, b):
    try:
        return math.pow(a, b)
    except OverflowError:
        return math.inf
    except ValueError:
        return math.nan if not (a == 0 and b < 0) else math.inf


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _tokenize(src: str) -> list[tuple]:
    src = src.lower().replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-").replace("π", "pi").replace("**", "^")
    if len(src) > 80:
        raise FormulaError("Formula too long (max 80 characters)")
    out, i = [], 0
    while i < len(src):
        ch = src[i]
        if ch == " ":
            i += 1
            continue
        m = re.match(r"(\d+\.?\d*|\.\d+)", src[i:])
        if m:
            out.append(("num", float(m.group(1)), i))
            i += len(m.group(1))
            continue
        m = re.match(r"[a-z]+", src[i:])
        if m:
            w = m.group(0)
            if w == "x":
                out.append(("x", None, i))
            elif w in CONSTS:
                out.append(("k", CONSTS[w], i))
            elif w in FUNCS:
                out.append(("fn", w, i))
            else:
                names = list(FUNCS) + ["x"] + list(CONSTS)
                best = min(names, key=lambda n: _lev(w, n))
                if _lev(w, best) <= 2:
                    raise FormulaError(f"Unknown '{w}'. Did you mean '{best}'?", i)
                raise FormulaError(f"Unknown name '{w}'. The only variable is x", i)
            i += len(w)
            continue
        if ch in "+-*/^(),":
            out.append((ch, None, i))
            i += 1
            continue
        raise FormulaError(f"Unexpected character '{ch}'", i)
    return out


_ENDS = {"num", "x", "k", ")"}
_STARTS = {"num", "x", "k", "fn", "("}


def _implicit(toks):
    out = []
    for t in toks:
        if out and out[-1][0] in _ENDS and t[0] in _STARTS:
            if out[-1][0] == "num" and t[0] == "num":
                raise FormulaError("Two numbers in a row: missing an operator?", t[2])
            out.append(("*", None, t[2]))
        out.append(t)
    return out


def compile_formula(src: str, level: int = 4):
    """-> (f, pretty). Raises FormulaError."""
    if not src.strip():
        raise FormulaError("Type a formula, for example  2x  or  x^2/10")
    T = _implicit(_tokenize(src))
    pos = [0]
    depth = [0]

    def peek():
        return T[pos[0]][0] if pos[0] < len(T) else None

    def fail(want=None):
        if pos[0] >= len(T):
            raise FormulaError("Missing ')'" if want == ")" else "The formula ends too early", len(src))
        t = T[pos[0]]
        raise FormulaError(f"Unexpected '{t[1] if t[1] is not None else t[0]}'" + (f", expected '{want}'" if want else ""), t[2])

    def eat(kind):
        if peek() == kind:
            pos[0] += 1
        else:
            fail(kind)

    def expr():
        l = term()
        while peek() in ("+", "-"):
            op = T[pos[0]][0]
            pos[0] += 1
            a, b = l, term()
            l = (lambda a, b: lambda x: a(x) + b(x))(a, b) if op == "+" else (lambda a, b: lambda x: a(x) - b(x))(a, b)
        return l

    def term():
        l = unary()
        while peek() in ("*", "/"):
            op = T[pos[0]][0]
            pos[0] += 1
            a, b = l, unary()
            l = (lambda a, b: lambda x: a(x) * b(x))(a, b) if op == "*" else (lambda a, b: lambda x: _div(a(x), b(x)))(a, b)
        return l

    def unary():
        if peek() == "-":
            pos[0] += 1
            a = unary()
            return lambda x: -a(x)
        if peek() == "+":
            pos[0] += 1
            return unary()
        return power()

    def power():
        base = atom()
        if peek() == "^":
            pos[0] += 1
            ex = unary()
            return lambda x: _pow(base(x), ex(x))
        return base

    def atom():
        depth[0] += 1
        if depth[0] > 40:
            raise FormulaError("Formula is nested too deeply")
        if pos[0] >= len(T):
            fail()
        kind, val, p = T[pos[0]]
        pos[0] += 1
        if kind in ("num", "k"):
            f = lambda x, v=val: v
        elif kind == "x":
            f = lambda x: x
        elif kind == "(":
            f = expr()
            eat(")")
        elif kind == "fn":
            arity, fn, lv = FUNCS[val]
            if lv > level:
                raise FormulaError(f"{val}() unlocks at level {lv}", p)
            if peek() != "(":
                raise FormulaError(f"{val} needs brackets: {val}(x)", p)
            pos[0] += 1
            args = [expr()]
            while len(args) < arity and peek() == ",":
                pos[0] += 1
                args.append(expr())
            if len(args) != arity:
                raise FormulaError(f"{val}() needs {arity} argument{'s' if arity > 1 else ''}", p)
            eat(")")
            if arity == 1:
                a = args[0]
                f = lambda x, a=a, fn=fn: fn(a(x))
            else:
                a, b = args
                f = lambda x, a=a, b=b, fn=fn: fn(a(x), b(x))
        else:
            pos[0] -= 1
            fail()
        depth[0] -= 1
        return f

    f = expr()
    if pos[0] < len(T):
        fail()
    return f, " ".join(str(t[1] if t[1] is not None else t[0]) if t[0] not in ("num",) else f"{t[1]:g}" for t in T)

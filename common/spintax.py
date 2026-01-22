import re


TOKEN_PATTERN = re.compile(r"\{\{#if\s+.+?\}\}|\{\{else\}\}|\{\{\/if\}\}")
IF_OPEN = re.compile(r"\{\{#if\s+.+?\}\}")
CONDITION_PATTERN = re.compile(r"\{\{#if\s+(\w+)\s+'=='\s+\"[^\"]+\"\s*\}\}")
CONDITION_PATTERN_SIMPLE = re.compile(r"\{\{#if\s+(\w+)\s*\}\}")


def context_snippet(text: str, pos: int, window: int = 40) -> str:
    start = max(0, pos - window)
    end = min(len(text), pos + window)
    snippet = text[start:end]
    pointer = " " * (pos - start) + "^"
    return f"{snippet}\n{pointer}"


def validate_if_blocks(text: str):
    stack = []

    for match in TOKEN_PATTERN.finditer(text):
        token = match.group()
        pos = match.start()

        if token.startswith("{{#if"):
            stack.append(pos)

        elif token == "{{else}}":
            if not stack:
                return {
                    "ok": False,
                    "error": "ELSE without matching IF",
                    "position": pos,
                    "context": context_snippet(text, pos),
                }

        elif token == "{{/if}}":
            if not stack:
                return {
                    "ok": False,
                    "error": "ENDIF without matching IF",
                    "position": pos,
                    "context": context_snippet(text, pos),
                }
            stack.pop()

    if stack:
        pos = stack[-1]
        return {
            "ok": False,
            "error": "IF without closing ENDIF",
            "position": pos,
            "context": context_snippet(text, pos),
        }

    return {"ok": True}


def validate_if_conditions(text: str):
    for match in IF_OPEN.finditer(text):
        token = match.group()
        pos = match.start()

        if not CONDITION_PATTERN.fullmatch(
            token
        ) and not CONDITION_PATTERN_SIMPLE.fullmatch(token):
            return {
                "ok": False,
                "error": "Invalid IF condition syntax",
                "position": pos,
                "context": context_snippet(text, pos),
            }

    return {"ok": True}


def validate_spintax(text: str):
    stack = []

    for i, c in enumerate(text):
        if c == "{":
            stack.append(i)
        elif c == "}":
            if not stack:
                return {
                    "ok": False,
                    "error": "Unmatched closing brace",
                    "position": i,
                    "context": context_snippet(text, i),
                }
            stack.pop()

    if stack:
        pos = stack[-1]
        return {
            "ok": False,
            "error": "Unclosed opening brace",
            "position": pos,
            "context": context_snippet(text, pos),
        }

    return {"ok": True}


def validate_template(text: str):
    checks = [
        validate_if_blocks,
        validate_if_conditions,
        validate_spintax,
    ]

    for check in checks:
        result = check(text)
        if not result["ok"]:
            return result

    return {"ok": True}

"""Edit application engine for surgical script refinement.

Applies a list of {old_code, new_code} edits sequentially to an existing script.
Uses a chain of 4 fuzzy matchers (strictest first) to locate each edit target.
Any failure triggers a full rollback — partial application is never returned.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EditResult:
    """Result of applying a batch of edits."""

    success: bool
    code: str
    applied_count: int
    error: str | None = None


def apply_edits(current_code: str, edits: list[dict]) -> EditResult:
    """Apply a list of edits sequentially to current_code.

    Each edit is a dict with "old_code" and "new_code" keys.  Edits are applied
    in order so that later edits can target text introduced by earlier ones.
    If any edit fails to locate its target, the original code is returned
    unchanged (atomic rollback).

    Args:
        current_code: The original script source.
        edits: List of {"old_code": str, "new_code": str} dicts.

    Returns:
        EditResult indicating success/failure and the (possibly modified) code.
    """
    if not edits:
        return EditResult(success=True, code=current_code, applied_count=0)

    working = current_code
    for i, edit in enumerate(edits):
        old_code = edit.get("old_code", "")
        new_code = edit.get("new_code", "")

        if not old_code:
            return EditResult(
                success=False,
                code=current_code,
                applied_count=0,
                error=f"Edit {i + 1}: old_code is empty",
            )

        match = locate_edit(working, old_code)
        if match is None:
            logger.warning(f"Edit {i + 1}: could not locate old_code in script")
            return EditResult(
                success=False,
                code=current_code,
                applied_count=0,
                error=f"Edit {i + 1}: old_code not found in script",
            )

        start, end = match
        working = working[:start] + new_code + working[end:]
        logger.debug(f"Edit {i + 1}: applied at [{start}:{end}]")

    return EditResult(success=True, code=working, applied_count=len(edits))


def locate_edit(code: str, old_code: str) -> tuple[int, int] | None:
    """Locate old_code inside code using a chain of fuzzy matchers.

    Matchers are tried strictest-first.  The first one that produces exactly
    one match wins.  If ExactReplacer finds multiple matches it raises
    immediately (no looser matcher can disambiguate an exact duplicate).

    Args:
        code: The current full script source.
        old_code: The target snippet to find.

    Returns:
        (start, end) character indices into *code*, or None if not found.

    Raises:
        ValueError: If old_code appears multiple times (ambiguous).
    """
    matchers = [
        _exact_match,
        _line_trimmed_match,
        _indentation_flexible_match,
        _blank_line_flexible_match,
    ]

    for matcher in matchers:
        result = matcher(code, old_code)
        if result is not None:
            return result

    return None


# ---------------------------------------------------------------------------
# Matcher 1 — ExactReplacer
# ---------------------------------------------------------------------------


def _exact_match(code: str, old_code: str) -> tuple[int, int] | None:
    """Exact substring search.  Raises on ambiguity (multiple occurrences)."""
    first = code.find(old_code)
    if first == -1:
        return None

    # Check for a second occurrence
    second = code.find(old_code, first + 1)
    if second != -1:
        raise ValueError(
            "old_code appears multiple times in script — edit is ambiguous"
        )

    return first, first + len(old_code)


# ---------------------------------------------------------------------------
# Matcher 2 — LineTrimmedReplacer
# ---------------------------------------------------------------------------


def _line_trimmed_match(code: str, old_code: str) -> tuple[int, int] | None:
    """Match after stripping trailing whitespace from every line.

    Maps the match position back to the original (untrimmed) code so that the
    returned indices are valid for slicing *code*.
    """
    trimmed_code, orig_starts = _build_trimmed_map(code)
    trimmed_old = "\n".join(line.rstrip() for line in old_code.split("\n"))

    pos = trimmed_code.find(trimmed_old)
    if pos == -1:
        return None

    # Ambiguity check
    if trimmed_code.find(trimmed_old, pos + 1) != -1:
        raise ValueError(
            "old_code (line-trimmed) appears multiple times — edit is ambiguous"
        )

    # Map trimmed positions back to original positions
    start_orig = _map_trimmed_pos_to_orig(code, trimmed_code, orig_starts, pos)
    end_trimmed = pos + len(trimmed_old)
    end_orig = _map_trimmed_pos_to_orig(code, trimmed_code, orig_starts, end_trimmed)

    return start_orig, end_orig


def _build_trimmed_map(code: str) -> tuple[str, list[int]]:
    """Build a line-trimmed version of code and a per-line start-offset map.

    Returns:
        (trimmed_text, orig_line_starts) where orig_line_starts[i] is the
        character offset of line i in the *original* code.
    """
    lines = code.split("\n")
    orig_starts: list[int] = []
    offset = 0
    for line in lines:
        orig_starts.append(offset)
        offset += len(line) + 1  # +1 for the \n
    trimmed = "\n".join(line.rstrip() for line in lines)
    return trimmed, orig_starts


def _map_trimmed_pos_to_orig(
    orig_code: str,
    trimmed_code: str,
    orig_line_starts: list[int],
    trimmed_pos: int,
) -> int:
    """Convert a character position in trimmed_code to one in orig_code."""
    # Which line does trimmed_pos fall on?
    trimmed_lines = trimmed_code.split("\n")
    offset = 0
    for line_idx, line in enumerate(trimmed_lines):
        line_end = offset + len(line)  # position just after this line's content
        if trimmed_pos <= line_end:
            # It's within this line (or right at its end)
            col = trimmed_pos - offset
            return orig_line_starts[line_idx] + col
        offset = line_end + 1  # +1 for \n

    # Past the end — return length of original
    return len(orig_code)


# ---------------------------------------------------------------------------
# Matcher 3 — IndentationFlexibleReplacer
# ---------------------------------------------------------------------------


def _indentation_flexible_match(code: str, old_code: str) -> tuple[int, int] | None:
    """Re-indent old_code to match indent levels present in code, then search.

    Detects the indent of the first non-blank line in old_code, then tries
    re-indenting old_code to every indent level found in code.  Returns the
    match only if exactly one indent level produces a hit.
    """
    old_indent = _detect_indent(old_code)
    if old_indent is None:
        return None  # all-blank old_code — nothing to do

    # Collect unique indent levels present in code
    code_indents = set()
    for line in code.split("\n"):
        stripped = line.lstrip()
        if stripped:
            code_indents.add(len(line) - len(stripped))

    matches: list[tuple[int, int, int]] = []  # (start, end, target_indent)
    for target_indent in code_indents:
        if target_indent == old_indent:
            continue  # already tried by exact / line-trimmed

        reindented = _reindent(old_code, old_indent, target_indent)
        pos = code.find(reindented)
        if pos == -1:
            continue

        # Check uniqueness at this indent level
        if code.find(reindented, pos + 1) != -1:
            raise ValueError(
                "old_code (re-indented) appears multiple times — edit is ambiguous"
            )
        matches.append((pos, pos + len(reindented), target_indent))

    if len(matches) == 1:
        return matches[0][0], matches[0][1]

    if len(matches) > 1:
        raise ValueError(
            "old_code matches at multiple indent levels — edit is ambiguous"
        )

    return None


def _detect_indent(text: str) -> int | None:
    """Return the indentation (number of leading spaces) of the first non-blank line."""
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped:
            return len(line) - len(stripped)
    return None


def _reindent(text: str, from_indent: int, to_indent: int) -> str:
    """Shift indentation of every line by (to_indent - from_indent) spaces.

    Lines that are blank (only whitespace) are left as empty strings to avoid
    adding spurious trailing spaces.
    """
    delta = to_indent - from_indent
    result_lines: list[str] = []
    for line in text.split("\n"):
        if not line.strip():
            result_lines.append("")
        else:
            current = len(line) - len(line.lstrip())
            new_indent = max(0, current + delta)
            result_lines.append(" " * new_indent + line.lstrip())
    return "\n".join(result_lines)


# ---------------------------------------------------------------------------
# Matcher 4 — BlankLineFlexibleReplacer
# ---------------------------------------------------------------------------


def _blank_line_flexible_match(code: str, old_code: str) -> tuple[int, int] | None:
    """Match after stripping all blank lines from both strings.

    This handles both directions: a blank line present in old_code but missing
    from code, and vice versa.  It is the most lossy normalization so it is
    tried last.  The returned indices refer to the *original* code span.
    """
    stripped_code, spans = _strip_blank_lines_with_spans(code)
    stripped_old = _strip_blank_lines(old_code)

    pos = stripped_code.find(stripped_old)
    if pos == -1:
        return None

    if stripped_code.find(stripped_old, pos + 1) != -1:
        raise ValueError(
            "old_code (blank-lines-stripped) appears multiple times — edit is ambiguous"
        )

    # Map stripped [pos, pos+len) back to original spans
    end_pos = pos + len(stripped_old)
    start_orig = _collapsed_pos_to_orig(spans, pos)
    end_orig = _collapsed_pos_to_orig(spans, end_pos)

    return start_orig, end_orig


def _strip_blank_lines(text: str) -> str:
    """Remove all blank lines from text."""
    return "\n".join(line for line in text.split("\n") if line.strip())


def _strip_blank_lines_with_spans(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Strip blank lines and record per-character mapping back to original positions.

    Returns:
        (stripped_text, spans) where spans[i] = (orig_start, orig_end) for the
        i-th character in stripped_text.  len(spans) == len(stripped_text).
    """
    lines = text.split("\n")
    kept_line_info: list[tuple[int, int]] = []  # (orig_char_start, line_length)

    orig_offset = 0
    for line in lines:
        if line.strip():
            kept_line_info.append((orig_offset, len(line)))
        orig_offset += len(line) + 1  # +1 for \n

    stripped_text = "\n".join(text.split("\n")[0:0])  # will rebuild below
    stripped_lines: list[str] = []
    for orig_start, length in kept_line_info:
        stripped_lines.append(text[orig_start : orig_start + length])
    stripped_text = "\n".join(stripped_lines)

    # Build per-character span map
    spans: list[tuple[int, int]] = []
    for line_idx, (orig_start, orig_len) in enumerate(kept_line_info):
        for col in range(orig_len):
            spans.append((orig_start + col, orig_start + col + 1))
        # \n separator between kept lines (not after the last one)
        if line_idx < len(kept_line_info) - 1:
            spans.append((orig_start + orig_len, orig_start + orig_len + 1))

    return stripped_text, spans


def _collapsed_pos_to_orig(spans: list[tuple[int, int]], pos: int) -> int:
    """Map a position in collapsed text to the corresponding original position."""
    if pos <= 0:
        return 0
    if pos >= len(spans):
        # Past end — return one past the last span's end
        return spans[-1][1] if spans else 0
    return spans[pos][0]

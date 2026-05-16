import re

from num2words import num2words
from word2number import w2n

from apps.channels.models import Stream

from .base import WaybillTransformerBase

# Words (lowercased) that can START a cardinal-number span.
# "and" is intentionally excluded: it may only appear *inside* an existing span
# (e.g. "one hundred and one") because word2number silently accepts leading
# "and" — allowing it to start a span would silently consume "and" in phrases
# like "BBC One and ITV Two".
_NUMBER_WORDS_LEADING: frozenset[str] = frozenset(
    [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
        "thousand",
        "million",
        "billion",
    ]
)

# Words that may *continue* an existing span.  Adds "and" so that phrases like
# "one hundred and one" are captured atomically before conversion.
_NUMBER_WORDS_INNER: frozenset[str] = _NUMBER_WORDS_LEADING | {"and"}


def _is_leading_number_token(token: str) -> bool:
    """Return True if every hyphen-delimited component of *token* is a leading number word."""
    return bool(token) and all(
        part.lower() in _NUMBER_WORDS_LEADING for part in token.split("-")
    )


def _is_inner_number_token(token: str) -> bool:
    """Return True if every hyphen-delimited component of *token* is an inner number word."""
    return bool(token) and all(
        part.lower() in _NUMBER_WORDS_INNER for part in token.split("-")
    )


def _scan_and_replace_number_words(text: str, word_to_num_fn) -> str:
    """Replace maximal number-word spans in *text* with their numeric values.

    Tokenises *text* on whitespace, then scans left-to-right to identify
    maximal contiguous spans of number-word tokens.  Hyphen-joined compounds
    (e.g. ``Twenty-One``) are treated as single tokens.  Spans may cross word
    boundaries (e.g. ``One Hundred And One``) so that multi-word expressions
    are converted atomically rather than piecemeal.

    A greedy longest-match strategy is used: the full span is tried first, then
    progressively shorter prefixes until one converts cleanly.  Sub-phrases
    ending in ``and`` are skipped during matching because *word2number* silently
    tolerates trailing ``and`` connectors — accepting such a phrase would
    incorrectly consume the ``and`` that belongs to the surrounding prose.
    """
    # re.split with a capturing group yields alternating [word, sep, word, …]
    # with possible empty strings at the start/end when whitespace is at the boundaries.
    pieces = re.split(r"(\s+)", text)
    output: list[str] = []
    i = 0

    while i < len(pieces):
        piece = pieces[i]

        # Pass whitespace and empty tokens through unchanged.
        if not piece or re.fullmatch(r"\s+", piece):
            output.append(piece)
            i += 1
            continue

        if not _is_leading_number_token(piece):
            output.append(piece)
            i += 1
            continue

        # Accumulate a maximal span: leading word + (space, word)* while each
        # subsequent word satisfies _is_inner_number_token.
        words: list[str] = [piece]
        j = i + 1
        while j + 1 < len(pieces):
            space, next_word = pieces[j], pieces[j + 1]
            if re.fullmatch(r"\s+", space) and _is_inner_number_token(next_word):
                words.append(next_word)
                j += 2
            else:
                break

        # Greedy longest-match conversion, shrinking from the right.
        # Skip any candidate whose last word is "and": word2number silently
        # drops trailing "and" connectors, which would produce incorrect
        # truncations such as "One And [ITV]" → "1".
        matched = 0
        converted: str | None = None
        for length in range(len(words), 0, -1):
            if words[length - 1].lower() == "and":
                continue
            phrase = " ".join(words[:length])
            result = word_to_num_fn(phrase)
            if result != phrase:
                matched = length
                converted = result
                break

        if matched:
            output.append(converted)
            # We consumed `matched` word tokens; each word beyond the first was
            # preceded by exactly one whitespace token, so advance by
            # 2 * matched − 1 pieces.
            i += 2 * matched - 1
        else:
            # No conversion possible; emit the leading word as-is and retry.
            output.append(words[0])
            i += 1

    return "".join(output)


class WaybillTransformerConvertCardinalNumbers(WaybillTransformerBase):
    def __init__(self, output_type: str, field: str = "name"):
        self.output_type = output_type
        self.field = field

    def _word_to_num(self, phrase: str) -> str:
        """Convert a number-word phrase to its digit string.

        *phrase* may be a single word (``"one"``), a hyphenated compound
        (``"twenty-one"``), or a multi-word expression
        (``"one hundred and one"``).  Returns the original phrase unchanged
        if conversion fails.
        """
        try:
            return str(w2n.word_to_num(phrase.lower()))
        except ValueError:
            return phrase

    def _num_to_word(self, num: str) -> str:
        try:
            return num2words(int(num)).upper()
        except ValueError:
            return num

    def transform(
        self, stream: Stream, variables: "dict[str, str] | None" = None
    ) -> "Stream | None":
        value = getattr(stream, self.field)
        match self.output_type:
            case "number":
                value = _scan_and_replace_number_words(value, self._word_to_num)
            case "word":
                value = re.sub(
                    r"\b\d+\b",
                    lambda m: self._num_to_word(m.group(0)),
                    value,
                )
        setattr(stream, self.field, value)
        return stream

    def _describe_self(self) -> str:
        field_note = f' on "{self.field}"' if self.field != "name" else ""
        return f"convertCardinalNumbers(\u2192 {self.output_type}){field_note}"

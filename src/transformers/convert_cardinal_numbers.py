import re

from num2words import num2words
from word2number import w2n

from apps.channels.models import Stream


class WaybillTransformerConvertCardinalNumbers:
    def __init__(self, direction: str, output_type: str, field: str = "name"):
        self.direction = direction
        self.output_type = output_type
        self.field = field

    def _word_to_num(self, word: str) -> str:
        try:
            return str(w2n.word_to_num(word.lower()))
        except ValueError:
            return word

    def transform(self, stream: Stream) -> Stream | None:
        value = getattr(stream, self.field)
        if self.output_type == "number":
            value = re.sub(
                r"\b[a-zA-Z]+\b",
                lambda m: self._word_to_num(m.group(0)),
                value,
            )
        elif self.output_type == "word":
            value = re.sub(
                r"\b\d+\b",
                lambda m: num2words(int(m.group(0))).upper(),
                value,
            )
        setattr(stream, self.field, value)
        return stream

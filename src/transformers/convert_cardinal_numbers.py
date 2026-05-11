import re

from num2words import num2words
from word2number import w2n

from apps.channels.models import Stream

from .base import WaybillTransformerBase


class WaybillTransformerConvertCardinalNumbers(WaybillTransformerBase):
    def __init__(self, output_type: str, field: str = "name"):
        self.output_type = output_type
        self.field = field

    def _word_to_num(self, word: str) -> str:
        try:
            return str(w2n.word_to_num(word.lower()))
        except ValueError:
            return word

    def _num_to_word(self, num: str) -> str:
        try:
            return num2words(int(num)).upper()
        except ValueError:
            return num

    def transform(self, stream: Stream) -> Stream | None:
        value = getattr(stream, self.field)
        match self.output_type:
            case "number":
                value = re.sub(
                    r"\b[a-zA-Z]+\b",
                    lambda m: self._word_to_num(m.group(0)),
                    value,
                )
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

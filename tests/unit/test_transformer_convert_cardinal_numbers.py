"""Tests for WaybillTransformerConvertCardinalNumbers.

Unit tests use a monkeypatched ``_word_to_num`` to focus on the scanner's
structural behaviour — what phrases are assembled and passed to the conversion
function — without coupling to the vendored libraries.

Integration tests (``TestConvertCardinalNumbersIntegration``) use the real
vendored num2words / word2number via the ``real_number_libs`` fixture defined
in conftest.py.
"""

from __future__ import annotations

import pytest

from src.transformers.convert_cardinal_numbers import (
    WaybillTransformerConvertCardinalNumbers,
)


@pytest.fixture()
def number_transformer(stream_factory):
    """A word→number transformer operating on the ``name`` field."""
    return WaybillTransformerConvertCardinalNumbers(output_type="number")


@pytest.fixture()
def word_transformer():
    """A digit→word transformer operating on the ``name`` field."""
    return WaybillTransformerConvertCardinalNumbers(output_type="word")


class TestSingleWordConversion:
    def test_number_word_replaced(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            number_transformer,
            "_word_to_num",
            lambda w: "3" if w.lower() == "three" else w,
        )
        s = stream_factory(name="Channel Three")
        number_transformer.transform(s)
        assert s.name == "Channel 3"

    def test_non_number_words_left_unchanged(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(number_transformer, "_word_to_num", lambda w: w)
        s = stream_factory(name="NBS HD")
        number_transformer.transform(s)
        assert s.name == "NBS HD"

    def test_existing_digits_left_unchanged(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(number_transformer, "_word_to_num", lambda w: w)
        s = stream_factory(name="NBS 1")
        number_transformer.transform(s)
        assert s.name == "NBS 1"

    def test_returns_stream_instance(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(number_transformer, "_word_to_num", lambda w: w)
        s = stream_factory()
        assert number_transformer.transform(s) is s

    def test_operates_on_specified_field(self, stream_factory, monkeypatch) -> None:
        t = WaybillTransformerConvertCardinalNumbers(
            output_type="number", field="tvg_id"
        )
        monkeypatch.setattr(
            t, "_word_to_num", lambda w: "3" if w.lower() == "three" else w
        )
        s = stream_factory(tvg_id="channel three")
        t.transform(s)
        assert s.tvg_id == "channel 3"

    def test_word_to_num_returns_original_on_error(self, number_transformer) -> None:
        assert number_transformer._word_to_num("not-a-number") == "not-a-number"


class TestHyphenatedCompound:
    """Regression tests: the old r'\\b[a-zA-Z]+\\b' regex split 'Twenty-One'."""

    def test_hyphenated_word_passed_as_single_phrase(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        seen: list[str] = []

        def recording(phrase: str) -> str:
            seen.append(phrase)
            return phrase

        monkeypatch.setattr(number_transformer, "_word_to_num", recording)
        number_transformer.transform(stream_factory(name="Channel Twenty-One"))
        assert "Twenty-One" in seen, f"Hyphenated token was split; phrases seen: {seen}"


class TestMultiWordSpanAssembly:
    """The scanner must assemble maximal number phrases across whitespace."""

    def test_two_word_phrase_assembled(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        seen: list[str] = []

        def recording(phrase: str) -> str:
            seen.append(phrase)
            return "100" if phrase.lower() == "one hundred" else phrase

        monkeypatch.setattr(number_transformer, "_word_to_num", recording)
        s = stream_factory(name="Channel One Hundred HD")
        number_transformer.transform(s)
        assert any("One Hundred" in p for p in seen)
        assert s.name == "Channel 100 HD"

    def test_four_word_phrase_assembled_atomically(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        seen: list[str] = []

        def recording(phrase: str) -> str:
            seen.append(phrase)
            return "101" if phrase.lower() == "one hundred and one" else phrase

        monkeypatch.setattr(number_transformer, "_word_to_num", recording)
        s = stream_factory(name="Channel One Hundred And One")
        number_transformer.transform(s)
        assert any(p.lower() == "one hundred and one" for p in seen), (
            f"Full phrase was not assembled; seen: {seen}"
        )
        assert s.name == "Channel 101"


class TestAndConnectorHandling:
    """'And' used as a conjunction between unrelated words must not start a span."""

    def test_standalone_and_preserved(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            number_transformer,
            "_word_to_num",
            lambda p: "1" if p.lower() == "one" else p,
        )
        s = stream_factory(name="NBS One And VTN Two")
        number_transformer.transform(s)
        assert "And" in s.name or "AND" in s.name
        assert s.name.startswith("NBS 1 And") or s.name.startswith("NBS 1 AND")

    def test_trailing_and_not_consumed_by_span(
        self, number_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            number_transformer,
            "_word_to_num",
            lambda p: "1" if p.lower() in ("one", "one and") else p,
        )
        s = stream_factory(name="NBS One And VTN")
        number_transformer.transform(s)
        assert "And" in s.name or "AND" in s.name


class TestWordMode:
    """digit → word conversion."""

    def test_digit_replaced_with_word(
        self, word_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            word_transformer, "_num_to_word", lambda n: "ONE" if n == "1" else n
        )
        s = stream_factory(name="Channel 1")
        word_transformer.transform(s)
        assert s.name == "Channel ONE"

    def test_non_digit_words_unchanged(
        self, word_transformer, stream_factory, monkeypatch
    ) -> None:
        monkeypatch.setattr(word_transformer, "_num_to_word", lambda n: n)
        s = stream_factory(name="NBS Sport")
        word_transformer.transform(s)
        assert s.name == "NBS Sport"

    def test_multiple_digits_all_converted(
        self, word_transformer, stream_factory, monkeypatch
    ) -> None:
        conversions = {"1": "ONE", "2": "TWO"}
        monkeypatch.setattr(
            word_transformer, "_num_to_word", lambda n: conversions.get(n, n)
        )
        s = stream_factory(name="Channel 1 and 2")
        word_transformer.transform(s)
        assert s.name == "Channel ONE and TWO"


class TestDescribe:
    def test_number_mode_describe(self, number_transformer) -> None:
        assert "number" in number_transformer.describe()
        assert "convertCardinalNumbers" in number_transformer.describe()

    def test_word_mode_describe(self, word_transformer) -> None:
        assert "word" in word_transformer.describe()

    def test_non_default_field_included_in_describe(self) -> None:
        t = WaybillTransformerConvertCardinalNumbers(
            output_type="number", field="tvg_id"
        )
        assert "tvg_id" in t.describe()


class TestConvertCardinalNumbersIntegration:
    """End-to-end tests using the real vendored num2words / word2number."""

    @pytest.fixture(autouse=True)
    def _use_real_libs(self, real_number_libs) -> None:  # noqa: PT004
        pass

    def _t(self, output_type: str) -> WaybillTransformerConvertCardinalNumbers:
        return WaybillTransformerConvertCardinalNumbers(output_type=output_type)

    @pytest.mark.parametrize(
        "digit_form, word_form",
        [
            ("Channel 1", "Channel ONE"),
            ("NBS 1 HD 2", "NBS ONE HD TWO"),
        ],
    )
    def test_digit_to_word(self, digit_form, word_form, stream_factory) -> None:
        s = stream_factory(name=digit_form)
        self._t("word").transform(s)
        assert s.name == word_form

    @pytest.mark.parametrize(
        "word_form, digit",
        [
            ("One", "1"),
            ("Four", "4"),
        ],
    )
    def test_single_word_to_number(self, word_form, digit, stream_factory) -> None:
        s = stream_factory(name=f"Channel {word_form}")
        self._t("number").transform(s)
        assert s.name == f"Channel {digit}"

    def test_non_number_words_unchanged(self, stream_factory) -> None:
        s = stream_factory(name="NBS HD")
        self._t("number").transform(s)
        assert s.name == "NBS HD"

    @pytest.mark.parametrize(
        "word_form, digit",
        [
            ("Twenty-One", "21"),
            ("Ninety-Nine", "99"),
        ],
    )
    def test_hyphenated_compound_to_number(
        self, word_form, digit, stream_factory
    ) -> None:
        s = stream_factory(name=f"Channel {word_form}")
        self._t("number").transform(s)
        assert s.name == f"Channel {digit}"

    @pytest.mark.parametrize(
        "word_form, digit",
        [
            ("One Hundred", "100"),
            ("One Hundred And One", "101"),
            ("One Hundred And Ten", "110"),
            ("One Hundred And Twenty-One", "121"),
            ("Two Hundred", "200"),
            ("One Thousand", "1000"),
        ],
    )
    def test_multi_word_to_number(self, word_form, digit, stream_factory) -> None:
        s = stream_factory(name=f"Channel {word_form}")
        self._t("number").transform(s)
        assert s.name == f"Channel {digit}"

    def test_and_connector_between_channels_preserved(self, stream_factory) -> None:
        s = stream_factory(name="NBS One And VTN Two")
        self._t("number").transform(s)
        assert s.name == "NBS 1 And VTN 2"

    @pytest.mark.parametrize("n", range(1, 21))
    def test_round_trip_1_to_20(self, n, stream_factory) -> None:
        from num2words import num2words  # noqa: PLC0415

        word_form = num2words(n).upper()
        s = stream_factory(name=f"Channel {word_form}")
        self._t("number").transform(s)
        assert s.name == f"Channel {n}", f"Round-trip failed for {n}: got {s.name!r}"

    @pytest.mark.parametrize("n", [21, 22, 42, 55, 71, 99])
    def test_round_trip_hyphenated_tens(self, n, stream_factory) -> None:
        from num2words import num2words  # noqa: PLC0415

        word_form = num2words(n).upper()
        assert "-" in word_form, f"Expected hyphen in {word_form!r} for {n}"
        s = stream_factory(name=f"Channel {word_form}")
        self._t("number").transform(s)
        assert s.name == f"Channel {n}", (
            f"Round-trip failed for {n} ({word_form!r}): got {s.name!r}"
        )

    @pytest.mark.parametrize("n", [100, 101, 110, 121, 200, 1000])
    def test_round_trip_hundreds_and_thousands(self, n, stream_factory) -> None:
        from num2words import num2words  # noqa: PLC0415

        word_form = num2words(n).upper()
        s = stream_factory(name=f"Channel {word_form}")
        self._t("number").transform(s)
        assert s.name == f"Channel {n}", (
            f"Round-trip failed for {n} ({word_form!r}): got {s.name!r}"
        )

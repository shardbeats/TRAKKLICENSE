"""Minimal number → words for *_WORD variables (EN + ES).

Covers 0..999999 + money decimals. No external deps.
Not a full i18n library on purpose (keep it light).
"""

_EN_0_19 = ["zero","one","two","three","four","five","six","seven","eight","nine",
            "ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen",
            "seventeen","eighteen","nineteen"]
_EN_TENS = ["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
_ES_0_19 = ["cero","uno","dos","tres","cuatro","cinco","seis","siete","ocho","nueve",
            "diez","once","doce","trece","catorce","quince","dieciséis",
            "diecisiete","dieciocho","diecinueve"]
_ES_TENS = ["","","veinte","treinta","cuarenta","cincuenta","sesenta","setenta","ochenta","noventa"]


def _en_under_1000(n: int) -> str:
    assert 0 <= n < 1000
    if n < 20:
        return _EN_0_19[n]
    if n < 100:
        t, r = divmod(n, 10)
        return _EN_TENS[t] if r == 0 else f"{_EN_TENS[t]}-{_EN_0_19[r]}"
    h, r = divmod(n, 100)
    return f"{_EN_0_19[h]} hundred" if r == 0 else f"{_EN_0_19[h]} hundred {_en_under_1000(r)}"


def _es_under_100(n: int) -> str:
    if n < 20:
        return _ES_0_19[n]
    if n < 30:
        return "veinte" if n == 20 else f"veinti{_ES_0_19[n-20]}"
    t, r = divmod(n, 10)
    return _ES_TENS[t] if r == 0 else f"{_ES_TENS[t]} y {_ES_0_19[r]}"


def _es_under_1000(n: int) -> str:
    assert 0 <= n < 1000
    if n < 100:
        return _es_under_100(n)
    if n == 100:
        return "cien"
    h, r = divmod(n, 100)
    base = "ciento" if h == 1 else ("quinientos" if h == 5 else f"{_ES_0_19[h]}cientos")
    # fix 700/900 irregular in short form
    if h == 7:
        base = "setecientos"
    if h == 9:
        base = "novecientos"
    return base if r == 0 else f"{base} {_es_under_100(r)}"


def number_to_words(n: int, lang: str = "en") -> str:
    """Integer 0..999999 → words."""
    if not (0 <= n <= 999999):
        raise ValueError("out of range 0..999999")
    lang = lang.lower()
    thou, rest = divmod(n, 1000)
    if lang.startswith("es"):
        parts = []
        if thou:
            parts.append("mil" if thou == 1 else f"{_es_under_1000(thou)} mil")
        if rest or not parts:
            parts.append(_es_under_1000(rest))
        return " ".join(parts)
    parts = []
    if thou:
        parts.append(f"{_en_under_1000(thou)} thousand")
    if rest or not parts:
        parts.append(_en_under_1000(rest))
    return " ".join(parts)


def money_to_words(amount: float, lang: str = "en", currency: str | None = None) -> str:
    """e.g. 300 -> 'three hundred USD'; cents kept: 49.99 -> 'forty-nine and 99/100 USD'."""
    from .policy import DEFAULT_CURRENCY
    currency = currency or DEFAULT_CURRENCY
    whole = int(amount)
    cents = round((amount - whole) * 100)
    if cents == 100:  # 0.999 float edge
        whole, cents = whole + 1, 0
    words = number_to_words(whole, lang)
    if cents:
        return f"{words} and {cents:02d}/100 {currency}"
    return f"{words} {currency}"

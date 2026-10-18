from app.engine.money_words import number_to_words, money_to_words


def test_en_basic():
    assert number_to_words(0) == "zero"
    assert number_to_words(300) == "three hundred"
    assert number_to_words(2500) == "two thousand five hundred"


def test_es_basic():
    assert number_to_words(300, "es") == "trescientos"
    assert number_to_words(2500, "es") == "dos mil quinientos"
    assert number_to_words(1, "es") == "uno"


def test_money():
    assert money_to_words(300, "en", "MXN") == "three hundred MXN"

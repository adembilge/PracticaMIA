from app.rag.language import detect_language


def test_english_question():
    assert detect_language("How do I renew a residence permit?") == ("en", False)


def test_italian_question():
    assert detect_language("Come rinnovo il permesso di soggiorno?") == ("it", False)


def test_turkish_question(monkeypatch):
    monkeypatch.setattr("app.rag.language._top_lang", lambda _text: ("tr", 0.99))
    assert detect_language("Oturum iznimi nasıl yenilerim?") == ("en", True)


def test_below_threshold_word_count_italian(monkeypatch):
    monkeypatch.setattr("app.rag.language._top_lang", lambda _text: ("en", 0.5))
    assert detect_language("come il che per non sono") == ("it", False)


def test_below_threshold_word_count_english(monkeypatch):
    monkeypatch.setattr("app.rag.language._top_lang", lambda _text: ("it", 0.5))
    assert detect_language("how do the and what is") == ("en", False)


def test_word_count_when_top_lang_raises(monkeypatch):
    import langdetect

    def _raise(_text: str):
        raise langdetect.LangDetectException(0, "langdetect failed")

    monkeypatch.setattr("app.rag.language._top_lang", _raise)
    assert detect_language("come il lo la") == ("it", False)
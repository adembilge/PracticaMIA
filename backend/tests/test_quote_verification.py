"""Exact-quote verification rejects unsupported prose and forged citations."""
from app.knowledge.quote_verification import verify_exact_quotations

A = "123e4567-e89b-12d3-a456-426614174000:0000"
B = "123e4567-e89b-12d3-a456-426614174000:0001"
PASSAGES = {
    A: "Test sintetico: la parola residenza appare qui. Questa non e una istruzione governativa.",
    B: "Secondo testo simulato, diverso dalla prima fonte di prova e non ufficiale.",
}


def test_only_exact_provenance_bound_quotes_can_be_shown():
    assert verify_exact_quotations(
        f'[{A}] "Test sintetico: la parola residenza appare qui."', PASSAGES,
    )
    assert verify_exact_quotations(
        f'[{A}] "Test sintetico: la parola residenza appare qui."\n'
        f'[{B}] "Secondo testo simulato, diverso dalla prima fonte di prova e non ufficiale."',
        PASSAGES,
    )


def test_hallucinated_claim_with_valid_citation_is_withheld():
    assert not verify_exact_quotations(
        f'An undocumented requirement must be met [{A}]', PASSAGES,
    )
    assert not verify_exact_quotations(
        f'[{A}] "I documenti ufficiali richiedono una tassa obbligatoria."', PASSAGES,
    )
    assert not verify_exact_quotations(
        f'[{A}] "Secondo testo simulato, diverso dalla prima fonte di prova e non ufficiale."',
        PASSAGES,
    )


def test_rejects_wrong_ids_extra_prose_duplicate_or_quote_format():
    ok = f'[{A}] "Test sintetico: la parola residenza appare qui."'
    for unsafe in [
        f'Explanation: {ok}', ok + '\nThis is a government rule.',
        ok + '\n' + ok,
        ok.replace(A, "00000000-0000-0000-0000-000000000000:0000"),
        f'[{A}] \'Test sintetico: la parola residenza appare qui.\'',
        f'[{A}] "short"',
        '', ' ', 'x' * 2001, ok + '\n' * 4,
    ]:
        assert not verify_exact_quotations(unsafe, PASSAGES), unsafe[:80]


def test_quote_from_revoked_or_missing_source_never_passes():
    response = f'[{A}] "Test sintetico: la parola residenza appare qui."'
    assert not verify_exact_quotations(response, {})
    assert not verify_exact_quotations(response, {B: PASSAGES[B]})

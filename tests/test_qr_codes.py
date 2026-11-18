from app.security.qr_codes import (
    QR_CODE_ALPHABET,
    QR_CODE_LENGTH,
    generate_qr_code,
    normalize_qr_code,
)


def test_generate_qr_code_uses_short_readable_alphabet():
    code = generate_qr_code()

    assert len(code) == QR_CODE_LENGTH
    assert set(code) <= set(QR_CODE_ALPHABET)


def test_qr_code_alphabet_avoids_ambiguous_characters():
    for character in "01IOL":
        assert character not in QR_CODE_ALPHABET


def test_each_generated_qr_code_is_different():
    codes = {generate_qr_code() for _ in range(100)}

    assert len(codes) == 100


def test_normalize_qr_code_ignores_case_spaces_and_dashes():
    assert normalize_qr_code(" k7md-2qxp ") == "K7MD2QXP"


def test_normalize_qr_code_accepts_unsam_prefix():
    assert normalize_qr_code("UNSAM-TWHGLHOG") == "TWHGLHOG"
    assert normalize_qr_code("unsam-twhglhog") == "TWHGLHOG"


def test_normalize_qr_code_keeps_codes_that_start_with_unsam_letters():
    assert normalize_qr_code("UNSAMXYZ") == "UNSAMXYZ"

import datetime
import pymupdf as fitz
import pytest


def valid_tckn():
    digits = [1, 0, 0, 0, 0, 0, 0, 0, 1]
    d10 = (sum(digits[0::2]) * 7 - sum(digits[1::2])) % 10
    d11 = (sum(digits) + d10) % 10
    return ''.join(map(str, digits + [d10, d11]))


def sample_doc():
    doc = fitz.open()
    page = doc.new_page()
    lines = [f'TCKN: {valid_tckn()}', 'Hatalı: 12345678901',
             'IBAN: TR33 0006 1005 1978 6457 8413 26', 'Yanlış IBAN: TR00 0006 1005 1978 6457 8413 26',
             'E-posta: deniz.yilmaz@example.com', 'Telefon: 0532 123 45 67']
    for i, line in enumerate(lines):
        page.insert_text((50, 60 + 25 * i), line, fontsize=11)
    return doc


def test_tckn_and_iban_checksums():
    from redaction import valid_tckn as check_tckn, valid_iban
    assert check_tckn(valid_tckn())
    assert not check_tckn('12345678901')
    assert not check_tckn('01234567890')
    assert valid_iban('TR33 0006 1005 1978 6457 8413 26')
    assert not valid_iban('TR00 0006 1005 1978 6457 8413 26')


def test_find_sensitive_only_reports_checksum_valid_values():
    from redaction import find_sensitive
    with sample_doc() as doc:
        hits = find_sensitive(doc)
        found = {(h['kind'], h['text']) for h in hits}
        assert ('TCKN', valid_tckn()) in found
        assert ('IBAN', 'TR33 0006 1005 1978 6457 8413 26') in found
        assert ('E-posta', 'deniz.yilmaz@example.com') in found
        assert ('Telefon', '0532 123 45 67') in found
        assert not any('12345678901' == h['text'] or h['text'].startswith('TR00') for h in hits)
        assert all(h['page'] == 0 and not fitz.Rect(h['rect']).is_empty for h in hits)
        only_mail = find_sensitive(doc, kinds={'E-posta'})
        assert [h['kind'] for h in only_mail] == ['E-posta']


def test_redact_hits_removes_text_everywhere():
    from redaction import find_sensitive, redact_hits
    with sample_doc() as doc:
        redact_hits(doc, find_sensitive(doc))
        data = doc.tobytes(garbage=4, deflate=True)
    with fitz.open(stream=data, filetype='pdf') as result:
        text = result[0].get_text()
        for secret in (valid_tckn(), 'deniz.yilmaz@example.com', 'TR33', '0532'):
            assert secret not in text
        # Checksum-invalid look-alikes are not personal data and must stay.
        assert '12345678901' in text and 'TR00' in text


@pytest.fixture(scope='module')
def pfx(tmp_path_factory):
    return make_pfx(tmp_path_factory.mktemp('cert'))


def make_pfx(folder):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Test İmzacı')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=30))
            .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
            .sign(key, hashes.SHA256()))
    path = folder / 'test.pfx'
    path.write_bytes(pkcs12.serialize_key_and_certificates(
        b'test', key, cert, None, serialization.BestAvailableEncryption(b'sifre')))
    return path


def signed_bytes(pfx, tmp_path, password=None):
    from signing import sign_pdf
    with sample_doc() as doc:
        options = dict(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password) if password else {}
        data = doc.tobytes(**options)
    output = tmp_path / 'imzali.pdf'
    sign_pdf(data, output, pfx, 'sifre', page=0, rect=fitz.Rect(300, 700, 500, 760),
             reason='Onay', location='İstanbul', password=password)
    return output


def test_sign_and_verify(pfx, tmp_path):
    from signing import verify_signatures
    output = signed_bytes(pfx, tmp_path)
    results = verify_signatures(output.read_bytes())
    assert len(results) == 1
    result = results[0]
    assert result['intact'] and result['covers_document']
    assert 'Test İmzacı' in result['signer']
    assert result['reason'] == 'Onay'
    with fitz.open(output) as doc:
        assert doc.get_sigflags() > 0


def test_verify_detects_modification_after_signing(pfx, tmp_path):
    from signing import verify_signatures
    output = signed_bytes(pfx, tmp_path)
    with fitz.open(output) as doc:
        doc[0].insert_text((50, 400), 'Sonradan eklendi')
        tampered = doc.tobytes(incremental=False)
    results = verify_signatures(tampered)
    assert not results or not all(r['intact'] and r['covers_document'] for r in results)


def test_sign_keeps_password_protection(pfx, tmp_path):
    from signing import verify_signatures
    output = signed_bytes(pfx, tmp_path, password='gizli')
    with fitz.open(output) as doc:
        assert doc.needs_pass and doc.authenticate('gizli')
    assert verify_signatures(output.read_bytes(), password='gizli')[0]['intact']


def test_wrong_pfx_password_is_reported(pfx, tmp_path):
    from signing import sign_pdf
    with sample_doc() as doc:
        data = doc.tobytes()
    with pytest.raises(ValueError, match='Sertifika'):
        sign_pdf(data, tmp_path / 'x.pdf', pfx, 'yanlis', page=0, rect=fitz.Rect(300, 700, 500, 760))
    assert not (tmp_path / 'x.pdf').exists()


def test_editor_flags_signed_documents(pfx, tmp_path):
    from engine import Editor
    output = signed_bytes(pfx, tmp_path)
    editor = Editor()
    editor.open(output)
    assert editor.signed
    editor.new()
    assert not editor.signed

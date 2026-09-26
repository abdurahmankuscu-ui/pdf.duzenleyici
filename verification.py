"""Integration smoke check usable from the packaged executable."""
from pathlib import Path
import json
import pymupdf as fitz
import integrations
import advanced
from engine import add_text


def verify_package(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    results = {}
    with fitz.open() as doc:
        page = doc.new_page()
        add_text(page, fitz.Rect(40, 40, 550, 180), 'PDF Stüdyo entegrasyon testi. İstanbul, 2026.', 20)
        data = doc.tobytes()
    try:
        report = advanced.pdfa(data, folder / 'verified-pdfa.pdf')
        results['pdfa'] = {'compliant': report['compliant'], 'profile': report['profile']}
    except Exception as exc:
        results['pdfa'] = {'error': str(exc)}
    try:
        results['ai'] = {'models': advanced.ollama_models()} if integrations.ai_enabled() else {'state': 'disabled'}
    except Exception as exc:
        results['ai'] = {'error': str(exc)}
    try:
        devices = integrations.scanner_devices()
        results['scanner'] = {'devices': devices, 'state': 'available' if devices else 'awaiting_hardware'}
    except Exception as exc:
        results['scanner'] = {'error': str(exc)}
    (folder / 'result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return results


def _test_certificate(folder):
    """Throwaway self-signed certificate, created only inside the check folder."""
    import datetime
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Paket denetimi')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
            .sign(key, hashes.SHA256()))
    path = folder / 'denetim.pfx'
    path.write_bytes(pkcs12.serialize_key_and_certificates(
        b'denetim', key, cert, None, serialization.BestAvailableEncryption(b'denetim')))
    return path


def verify_features(folder):
    """Run the 2.4 features from inside the packaged executable, where missing
    frozen modules would only show up at runtime."""
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    results = {}

    def check(name, fn):
        try:
            results[name] = dict(ok=True, **(fn() or {}))
        except Exception as exc:
            results[name] = dict(ok=False, error=f'{type(exc).__name__}: {exc}')

    def signing_check():
        import signing
        with fitz.open() as doc:
            doc.new_page().insert_text((50, 60), 'Paket imza denetimi')
            data = doc.tobytes()
        output = folder / 'imzali.pdf'
        signing.sign_pdf(data, output, _test_certificate(folder), 'denetim', page=0,
                         rect=fitz.Rect(300, 700, 500, 760), reason='Denetim')
        report = signing.verify_signatures(output.read_bytes())
        assert report and report[0]['intact'] and report[0]['covers_document'], report
        return dict(signer=report[0]['signer'])

    def redaction_check():
        import redaction
        with fitz.open() as doc:
            doc.new_page().insert_text((50, 60), 'IBAN TR33 0006 1005 1978 6457 8413 26 deneme@example.com')
            hits = redaction.find_sensitive(doc)
            redaction.redact_hits(doc, hits)
            assert 'example.com' not in doc[0].get_text()
        return dict(hits=len(hits))

    def stamping_check():
        from stamping import stamp_pages
        with fitz.open() as doc:
            doc.new_page()
            stamp_pages(doc, '{bates}', 'Alt sağ', bates_prefix='PKT-')
            assert 'PKT-000001' in doc[0].get_text()

    def forms_check():
        from forms import add_field, flatten_forms
        with fitz.open() as doc:
            page = doc.new_page()
            add_field(page, fitz.Rect(50, 50, 250, 70), 'Açılır liste', 'secim', options=['A', 'B'])
            doc = fitz.open(stream=doc.tobytes(), filetype='pdf')
            flatten_forms(doc)
            assert not list(doc[0].widgets())

    def theme_check():
        from theme import stylesheet
        assert 'background:#1c2530' in stylesheet('Koyu')

    def updater_check():
        import updater
        from version import VERSION
        assert updater.parse_version(VERSION)
        return dict(version=VERSION)

    for name, fn in [('signing', signing_check), ('redaction', redaction_check), ('stamping', stamping_check),
                     ('forms', forms_check), ('theme', theme_check), ('updater', updater_check)]:
        check(name, fn)
    (folder / 'features.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return results

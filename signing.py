"""Certificate-based PAdES signatures (pyHanko) and offline signature verification."""
import io
from pathlib import Path
import pymupdf as fitz
from engine import atomic_write


def _load_signer(pfx_path, pfx_password):
    from pyhanko.sign import signers
    try:
        signer = signers.SimpleSigner.load_pkcs12(pfx_file=str(pfx_path),
                                                   passphrase=pfx_password.encode('utf-8'))
    except Exception:
        signer = None
    if signer is None:
        raise ValueError('Sertifika açılamadı. .pfx/.p12 dosyasını ve sertifika parolasını kontrol edin.')
    return signer


def _pdf_box(data, page, rect, password):
    """Convert a PyMuPDF (top-left origin, unrotated) rect into PDF user space."""
    with fitz.open(stream=data, filetype='pdf') as doc:
        if password:
            doc.authenticate(password)
        box = fitz.Rect(rect) * ~doc[page].transformation_matrix
    box.normalize()
    return tuple(round(v, 2) for v in (box.x0, box.y0, box.x1, box.y1))


def sign_pdf(data, output, pfx_path, pfx_password, *, page, rect, reason='', location='', password=None):
    """Sign PDF bytes into a new file. The signature is an incremental update; any
    later full rewrite of the file (normal editing and saving) invalidates it."""
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers, fields
    from pyhanko.stamp import TextStampStyle
    signer = _load_signer(pfx_path, pfx_password)
    with fitz.open(stream=data, filetype='pdf') as doc:
        protected = doc.needs_pass
        if protected and not (password and doc.authenticate(password)):
            raise ValueError('Parolalı belgeyi imzalamak için doğru belge parolası gerekli.')
    if protected:
        data = _pyhanko_encrypted(data, password)
    writer = IncrementalPdfFileWriter(io.BytesIO(data), strict=False)
    if protected:
        writer.encrypt(password)
    existing = {f.split('.')[-1] for f in _field_names(writer)}
    name = next(f'Imza{i}' for i in range(1, 1000) if f'Imza{i}' not in existing)
    fields.append_signature_field(writer, fields.SigFieldSpec(
        sig_field_name=name, on_page=page, box=_pdf_box(data, page, rect, password)))
    meta = signers.PdfSignatureMetadata(field_name=name, reason=reason or None, location=location or None,
                                        subfilter=fields.SigSeedSubFilter.PADES)
    style = TextStampStyle(stamp_text='Dijital olarak imzalayan:\n%(signer)s\nTarih: %(ts)s')
    result = io.BytesIO()
    signers.PdfSigner(meta, signer=signer, stamp_style=style).sign_pdf(writer, output=result)
    atomic_write(output, result.getvalue())
    return name


def _pyhanko_encrypted(data, password):
    """MuPDF stores /Encrypt as a direct object, which pyHanko cannot extend
    incrementally. Re-encrypt (AES-256) with pyHanko before signing."""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.pdf_utils.writer import copy_into_new_writer
    with fitz.open(stream=data, filetype='pdf') as doc:
        doc.authenticate(password)
        plain = doc.tobytes(encryption=fitz.PDF_ENCRYPT_NONE)
    writer = copy_into_new_writer(PdfFileReader(io.BytesIO(plain), strict=False))
    writer.encrypt(password, password)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _trust_roots():
    """Windows root store, loaded explicitly (no network, no deprecated OS lookup)."""
    import ssl
    from asn1crypto import x509
    roots = []
    for der, encoding, _ in getattr(ssl, 'enum_certificates', lambda _: [])('ROOT'):
        if encoding == 'x509_asn':
            try:
                roots.append(x509.Certificate.load(der))
            except Exception:
                pass
    return roots


def _field_names(writer):
    try:
        from pyhanko.sign.fields import enumerate_sig_fields
        return [name for name, *_ in enumerate_sig_fields(writer.prev)]
    except Exception:
        return []


def verify_signatures(data, password=None):
    """Offline check: integrity and coverage are cryptographic facts; certificate
    trust is reported separately because no revocation data is fetched."""
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko.sign.validation.status import SignatureCoverageLevel
    from pyhanko_certvalidator import ValidationContext
    reader = PdfFileReader(io.BytesIO(data), strict=False)
    if reader.security_handler is not None and password:
        reader.decrypt(password)
    results = []
    roots = _trust_roots()
    for signature in reader.embedded_signatures:
        status = validate_pdf_signature(signature, ValidationContext(trust_roots=roots, allow_fetching=False))
        cert = status.signing_cert
        results.append(dict(
            field=signature.field_name,
            signer=cert.subject.human_friendly if cert else 'Bilinmiyor',
            signed_at=status.signer_reported_dt,
            reason=signature.sig_object.get('/Reason'),
            intact=bool(status.intact and status.valid),
            trusted=bool(status.trusted),
            covers_document=status.coverage == SignatureCoverageLevel.ENTIRE_FILE,
            summary=status.summary()))
    return results


def verification_report(results):
    if not results:
        return 'Belgede dijital imza bulunamadı.'
    lines = []
    for r in results:
        state = ('GEÇERLİ — imzadan sonra değişiklik yok' if r['intact'] and r['covers_document'] else
                 'DİKKAT — imzadan sonra belge değiştirilmiş' if r['intact'] else
                 'GEÇERSİZ — imza bozuk veya belge değiştirilmiş')
        lines.append(f"{r['field']}: {state}\n"
                     f"  İmzalayan: {r['signer']}\n"
                     f"  Tarih: {r['signed_at'] or 'belirtilmemiş'}\n"
                     f"  Neden: {r['reason'] or '-'}\n"
                     f"  Sertifika güveni: {'güvenilir kök' if r['trusted'] else 'doğrulanamadı (kendinden imzalı veya çevrimdışı; iptal durumu denetlenmedi)'}")
    return '\n\n'.join(lines)

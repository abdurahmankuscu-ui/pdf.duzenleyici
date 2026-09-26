"""Opt-in real-engine tests, plus deterministic error-path regression tests."""
import os
from pathlib import Path
import pytest
import pymupdf as fitz
import advanced
import integrations
from engine import add_text


def sample_pdf(text):
    with fitz.open() as doc:
        page = doc.new_page()
        add_text(page, fitz.Rect(35, 35, 560, 400), text, 18)
        return doc.tobytes()


@pytest.mark.skipif(os.environ.get('TEST_PDFA') != '1', reason='Requires Ghostscript and veraPDF')
def test_real_pdfa_conversion(tmp_path):
    output = tmp_path / 'arsiv.pdf'
    result = advanced.pdfa(sample_pdf('Türkçe PDF/A test: İstanbul, 2026.'), output)
    assert result['compliant']
    assert 'failedRules="0"' in Path(str(output) + '.validation.xml').read_text(encoding='utf-8')
    with fitz.open(output) as doc:
        assert 'İstanbul' in doc[0].get_text()


@pytest.mark.skipif(os.environ.get('TEST_PDFA') != '1', reason='Requires Ghostscript and veraPDF')
def test_validator_rejects_regular_pdf(tmp_path):
    path = tmp_path / 'regular.pdf'
    path.write_bytes(sample_pdf('This is a regular PDF without PDF/A metadata.'))
    assert not integrations.validate_pdfa(path)['compliant']


@pytest.mark.skipif(os.environ.get('TEST_PDFA') != '1', reason='Requires Ghostscript')
def test_failed_validation_keeps_existing_destination(tmp_path, monkeypatch):
    output = tmp_path / 'existing.pdf'
    previous = sample_pdf('The existing document must remain unchanged.')
    output.write_bytes(previous)
    monkeypatch.setattr(integrations, 'validate_pdfa', lambda _: {'compliant': False})
    with pytest.raises(RuntimeError, match='Hedef dosya değiştirilmedi'):
        advanced.pdfa(sample_pdf('A new conversion that fails validation.'), output)
    assert output.read_bytes() == previous


def test_ai_empty_pdf_does_not_send_labels_as_content(monkeypatch):
    monkeypatch.setattr(advanced, 'ollama_models', lambda: ['test'])
    with fitz.open() as doc:
        for _ in range(4):
            doc.new_page()
        with pytest.raises(ValueError, match='yeterli metin'):
            advanced.ai_document(doc.tobytes(), 'test', 'summarize')


def test_ai_partial_text_is_reported(monkeypatch):
    monkeypatch.setattr(advanced, 'ollama_models', lambda: ['test'])
    with fitz.open(stream=sample_pdf('A readable page with sufficient text.'), filetype='pdf') as doc:
        doc.new_page()
        with pytest.raises(ValueError, match='Bazı sayfalarda'):
            advanced.ai_document(doc.tobytes(), 'test', 'summarize')


def test_ai_truncated_response_is_not_delivered(monkeypatch):
    monkeypatch.setattr(advanced, 'ollama_models', lambda: ['test'])
    monkeypatch.setattr(integrations, 'local_json', lambda *a, **kw: {
        'message': {'content': 'unfinished'}, 'done_reason': 'length'})
    with pytest.raises(RuntimeError, match='kesildi'):
        advanced.ai_document(sample_pdf('A readable page with enough text for a summary.'), 'test', 'summarize')


@pytest.mark.skipif(os.environ.get('TEST_AI') != '1', reason='Requires local Ollama model')
def test_real_ai_summary_and_translation(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, 'ai_enabled', lambda: True)
    data = sample_pdf('Project Atlas starts on 12 October 2026. The team has 8 people. '
                      'The first delivery contains 24 PDF reports. The project manager is Deniz.')
    summary = advanced.ai_document(data, integrations.DEFAULT_MODEL,
        'Belgeyi Türkçe olarak kısaca özetle. Tarihleri, sayıları ve özel isimleri koru.')
    translation = advanced.ai_document(data, integrations.DEFAULT_MODEL,
        'Belge metnini Türkçeye çevir. Tarihleri, sayıları ve özel isimleri koru. Yalnızca çeviriyi yaz.')
    (tmp_path / 'summary.txt').write_text(summary, encoding='utf-8')
    (tmp_path / 'translation.txt').write_text(translation, encoding='utf-8')
    for text in (summary, translation):
        assert all(value in text for value in ('2026', '8', '24', 'Deniz'))
        assert len(text) > 80

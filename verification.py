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

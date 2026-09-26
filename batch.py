"""Apply one operation to many PDFs; originals are never overwritten."""
import html
from pathlib import Path
import pymupdf as fitz
import advanced
from engine import atomic_write
from stamping import stamp_pages

OPERATIONS = ('Küçült', 'OCR', 'Filigran', 'Damga')


def _watermark(doc, text):
    for page in doc:
        r = page.rect
        box = fitz.Rect(r.x0 + 30, r.y0 + r.height / 2 - 50, r.x1 - 30, r.y0 + r.height / 2 + 50)
        page.insert_htmlbox(box * page.derotation_matrix, '<div style="text-align:center">' + html.escape(text) + '</div>',
                            css='* {font-family:sans-serif;font-size:40pt;color:#777777}', opacity=0.25,
                            rotate=page.rotation)


def _free_name(folder, name):
    target = folder / name
    counter = 1
    while target.exists():
        target = folder / f'{Path(name).stem} ({counter}){Path(name).suffix}'
        counter += 1
    return target


def _process(source, target, operation, options):
    data = Path(source).read_bytes()
    with fitz.open(stream=data, filetype='pdf') as doc:
        if doc.needs_pass:
            raise ValueError('Parolalı PDF atlandı. Önce parolasız kopyasını oluşturun.')
        if not doc.is_pdf or not len(doc):
            raise ValueError('Geçerli bir PDF değil.')
        if operation in ('Filigran', 'Damga'):
            if operation == 'Filigran':
                _watermark(doc, options['text'])
            else:
                stamp_pages(doc, options['template'], options['position'], size=options.get('size', 10),
                            start=options.get('start', 1), bates_prefix=options.get('bates_prefix', ''),
                            bates_digits=options.get('bates_digits', 6))
            atomic_write(target, doc.tobytes(garbage=4, deflate=True))
            return 'Tamamlandı'
    if operation == 'Küçült':
        before, after = advanced.compress_pdf(data, target, options.get('lossy', False))
        return f'{before/1024:.0f} KB → {after/1024:.0f} KB'
    if operation == 'OCR':
        advanced.ocr_pdf(data, target, options.get('language', 'tur+eng'))
        return 'Aranabilir metin eklendi'
    raise ValueError(f'Bilinmeyen işlem: {operation}')


def run_batch(files, output_dir, operation, options, progress=None):
    """Return one result per file; one failing file does not stop the batch."""
    output_dir = Path(output_dir).resolve()
    files = [Path(f) for f in files]
    if any(f.resolve().parent == output_dir for f in files):
        raise ValueError('Çıktı klasörü, kaynak dosyaların bulunduğu klasörden farklı olmalı.')
    if operation not in OPERATIONS:
        raise ValueError(f'Bilinmeyen işlem: {operation}')
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i, source in enumerate(files, 1):
        target = _free_name(output_dir, source.name)
        try:
            message = _process(source, target, operation, options)
            results.append(dict(file=source, output=target, ok=True, message=message))
        except Exception as exc:
            results.append(dict(file=source, output=None, ok=False, message=str(exc) or type(exc).__name__))
        if progress:
            progress((i, len(files)))
    return results


def report(results):
    ok = sum(r['ok'] for r in results)
    lines = [f'{ok} / {len(results)} dosya işlendi.', '']
    lines += [f"{'✓' if r['ok'] else '✗'} {r['file'].name}: {r['message']}" +
              (f" → {r['output'].name}" if r['ok'] else '') for r in results]
    return '\n'.join(lines)

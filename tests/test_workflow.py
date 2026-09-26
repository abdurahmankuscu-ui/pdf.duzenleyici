import pymupdf as fitz
import pytest


def make_pdf(path, pages=3, password=None):
    with fitz.open() as doc:
        for i in range(pages):
            doc.new_page().insert_text((50, 100), f'Sayfa içeriği {i+1}')
        options = dict(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password) if password else {}
        doc.save(path, **options)
    return path


def text_in(page, rect):
    return page.get_textbox(rect).strip()


def test_stamp_positions_templates_and_bates(tmp_path):
    from stamping import stamp_pages
    with fitz.open(make_pdf(tmp_path / 'a.pdf')) as doc:
        stamp_pages(doc, 'Sayfa {n} / {toplam}', 'Alt orta', size=10)
        stamp_pages(doc, '{bates}', 'Üst sağ', size=9, start=41, bates_prefix='DAVA-', bates_digits=6)
        page = doc[1]
        w, h = page.rect.width, page.rect.height
        assert 'Sayfa 2 / 3' in text_in(page, fitz.Rect(0, h - 60, w, h))
        assert 'DAVA-000042' in text_in(page, fitz.Rect(w / 2, 0, w, 60))
        assert 'DAVA-000042' not in text_in(page, fitz.Rect(0, 0, w / 2, 60))


def test_stamp_selected_pages_and_bad_template(tmp_path):
    from stamping import stamp_pages
    with fitz.open(make_pdf(tmp_path / 'a.pdf')) as doc:
        stamp_pages(doc, 'GİZLİ', 'Üst orta', pages=[0, 2])
        assert ['GİZLİ' in p.get_text() for p in doc] == [True, False, True]
        for bad in ('{olmayan}', '{n', ''):
            with pytest.raises(ValueError):
                stamp_pages(doc, bad, 'Alt orta')


def test_stamp_rotated_page_lands_in_visible_corner(tmp_path):
    from stamping import stamp_pages
    with fitz.open(make_pdf(tmp_path / 'a.pdf', pages=1)) as doc:
        page = doc[0]
        page.set_rotation(90)
        stamp_pages(doc, 'ALTBİLGİ', 'Alt orta')
        # Text coordinates are unrotated; map the word back to what the reader sees.
        word = next(w for w in page.get_text('words') if 'ALTB' in w[4])
        visible = fitz.Rect(word[:4]) * page.rotation_matrix
        assert visible.y0 > page.rect.height * 0.8
        # Upright for the reader: the word runs horizontally on the visible page.
        assert visible.width > visible.height
        assert abs((visible.x0 + visible.x1) / 2 - page.rect.width / 2) < page.rect.width * 0.2


def test_batch_processes_folder_without_overwriting(tmp_path):
    from batch import run_batch
    source = tmp_path / 'girdi'
    source.mkdir()
    make_pdf(source / 'bir.pdf')
    make_pdf(source / 'iki.pdf')
    make_pdf(source / 'kilitli.pdf', password='x')
    (source / 'bozuk.pdf').write_bytes(b'not a pdf')
    output = tmp_path / 'cikti'
    progress = []
    results = run_batch(sorted(source.glob('*.pdf')), output, 'Damga',
                        dict(template='{n}', position='Alt orta'), progress=progress.append)
    status = {r['file'].name: r['ok'] for r in results}
    assert status == {'bir.pdf': True, 'iki.pdf': True, 'kilitli.pdf': False, 'bozuk.pdf': False}
    assert 'parola' in next(r['message'] for r in results if r['file'].name == 'kilitli.pdf').lower()
    assert progress[-1] == (4, 4)
    with fitz.open(output / 'bir.pdf') as doc:
        assert '2' in text_in(doc[1], fitz.Rect(0, doc[1].rect.height - 60, doc[1].rect.width, doc[1].rect.height))
    again = run_batch([source / 'bir.pdf'], output, 'Filigran', dict(text='TASLAK'))
    assert again[0]['output'].name == 'bir (1).pdf'
    with pytest.raises(ValueError):
        run_batch([source / 'bir.pdf'], source, 'Filigran', dict(text='X'))


def test_batch_compress(tmp_path):
    from batch import run_batch
    make_pdf(tmp_path / 'a.pdf')
    result = run_batch([tmp_path / 'a.pdf'], tmp_path / 'out', 'Küçült', dict(lossy=False))[0]
    assert result['ok'] and result['output'].exists()


def test_recent_files(tmp_path):
    from session import Session
    s = Session(tmp_path / 'data')
    files = [make_pdf(tmp_path / f'{i}.pdf', pages=1) for i in range(12)]
    for f in files:
        s.add_recent(f)
    s.add_recent(files[3])
    recent = s.recent()
    assert recent[0] == str(files[3]) and len(recent) == 10
    files[11].unlink()
    assert str(files[11]) not in s.recent()


def test_recovery_roundtrip_keeps_password(tmp_path):
    from engine import Editor
    from session import Session
    s = Session(tmp_path / 'data')
    editor = Editor()
    editor.open(make_pdf(tmp_path / 'k.pdf', pages=1, password='gizli'), 'gizli')
    editor.change(lambda d: d[0].insert_text((50, 200), 'Kaydedilmemis'))
    s.save_recovery(editor)
    entries = s.recoveries()
    assert len(entries) == 1 and entries[0]['original'] == editor.path and entries[0]['protected']
    with fitz.open(entries[0]['file']) as doc:
        assert doc.needs_pass and doc.authenticate('gizli')
        assert 'Kaydedilmemis' in doc[0].get_text()
    # The password itself is never written to disk.
    assert b'gizli' not in (tmp_path / 'data' / 'recovery' / (entries[0]['id'] + '.json')).read_bytes()
    s.discard_recovery(editor)
    assert s.recoveries() == []

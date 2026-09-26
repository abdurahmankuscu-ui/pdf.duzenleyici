import io
import pymupdf as fitz
from PIL import Image
from engine import Editor, add_text
import advanced


def test_lossy_compression_preserves_text(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page()
        image = Image.effect_noise((2400, 2400), 80).convert('RGB')
        stream = io.BytesIO()
        image.save(stream, format='PNG')
        page.insert_image(fitz.Rect(0, 100, 595, 700), stream=stream.getvalue())
        add_text(page, fitz.Rect(20, 20, 550, 90), 'Keep searchable text')
        output = tmp_path / 'small.pdf'
        before, after = advanced.compress_pdf(doc.tobytes(), output, True)
        assert after < before
        with fitz.open(output) as check:
            assert 'Keep searchable text' in check[0].get_text()


def test_rotated_coordinates_and_crop():
    with fitz.open() as doc:
        page = doc.new_page()
        page.set_rotation(90)
        visible = fitz.Rect(20, 30, 200, 90)
        original = visible * page.derotation_matrix
        assert (original * page.rotation_matrix) == visible
        page.set_rotation(0)
        page.set_cropbox(fitz.Rect(20, 20, 500, 700))
        selection = fitz.Rect(10, 10, 400, 600)
        page.set_cropbox(selection + (page.cropbox_position.x, page.cropbox_position.y, page.cropbox_position.x, page.cropbox_position.y))
        assert page.rect.width == 390

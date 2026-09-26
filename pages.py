"""Operations on several pages at once (thumbnail selection and drag-and-drop)."""


def reorder(doc, order):
    if sorted(order) != list(range(len(doc))):
        raise ValueError('Sayfa sırası geçersiz.')
    doc.select(list(order))


def rotate_pages(doc, indices, angle=90):
    for i in indices:
        doc[i].set_rotation((doc[i].rotation + angle) % 360)


def delete_pages(doc, indices):
    if len(set(indices)) >= len(doc):
        raise ValueError('Belgede en az bir sayfa kalmalı.')
    doc.delete_pages(sorted(set(indices)))

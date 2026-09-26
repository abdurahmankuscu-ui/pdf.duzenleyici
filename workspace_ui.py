"""Desktop workspace layout and a small, consistent vector icon set."""
from PySide6.QtCore import Qt, QSize, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QToolButton, QMenu, QSpinBox, QLineEdit,
    QListWidget, QStackedWidget, QSizePolicy, QScrollArea, QGraphicsDropShadowEffect,
    QAbstractSpinBox)


PATHS = {
    'file': '<path d="M7 3h7l5 5v13H5V3z M14 3v6h5 M8 13h8 M8 17h5"/>',
    'open': '<path d="M3 7h7l2 2h9l-3 11H3z M3 7V4h7l2 3h7v2"/>',
    'plus': '<path d="M12 5v14 M5 12h14"/>',
    'save': '<path d="M4 3h14l3 3v15H3V3z M7 3v6h10V3 M7 21v-8h10v8"/>',
    'undo': '<path d="M8 5L3 10l5 5 M3 10h10a7 7 0 0 1 7 7"/>',
    'redo': '<path d="M16 5l5 5-5 5 M21 10H11a7 7 0 0 0-7 7"/>',
    'cursor': '<path d="M5 3l14 10-7 1-3 7z"/>',
    'text': '<path d="M4 5h16 M12 5v15 M8 20h8 M4 5v3 M20 5v3"/>',
    'edit': '<path d="M4 20l4-1L20 7l-4-4L4 15z M13 6l4 4"/>',
    'move': '<path d="M12 2v20 M2 12h20 M8 6l4-4 4 4 M8 18l4 4 4-4 M6 8l-4 4 4 4 M18 8l4 4-4 4"/>',
    'style': '<path d="M5 4h14v5H5z M17 9v4h-5v8 M10 21h4"/>',
    'erase': '<path d="M4 13l10-10 7 7-10 10H8z M9 8l7 7 M11 20h10"/>',
    'image': '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="M3 17l6-5 4 4 4-7 4 6"/>',
    'mark': '<path d="M5 15l9-12 6 5-9 12z M5 15l6 5 M3 22h18"/>',
    'rect': '<rect x="4" y="5" width="16" height="14" rx="2"/>',
    'note': '<path d="M4 3h16v13l-5 5H4z M15 21v-6h5 M8 8h8 M8 12h5"/>',
    'crop': '<path d="M6 2v16h16 M2 6h16v16"/>',
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    'search': '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
    'scan': '<path d="M3 8V3h5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5 M3 12h18"/>',
    'chevron': '<path d="M9 5l7 7-7 7"/>',
    'pages': '<rect x="7" y="3" width="14" height="17" rx="2"/><path d="M3 7v15h14"/>',
    'fit': '<path d="M3 9V3h6 M15 3h6v6 M21 15v6h-6 M9 21H3v-6"/>',
    'pen': '<path d="M3 17c3-6 5 2 8-3s4-7 7-4 M16 4l4 4"/>',
    'line': '<path d="M4 20L20 4"/>',
    'arrow': '<path d="M4 20L20 4 M11 4h9v9"/>',
    'circle': '<circle cx="12" cy="12" r="8"/>',
    'link': '<path d="M10 14a4 4 0 0 0 5.6 0l3-3a4 4 0 0 0-5.6-5.6l-1 1 M14 10a4 4 0 0 0-5.6 0l-3 3a4 4 0 0 0 5.6 5.6l1-1"/>',
}


def icon(name, color='#526177'):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name, PATHS["file"])}</g></svg>'
    pix = QPixmap(48,48)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)



def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


def frame(name, vertical=False, margins=(0,0,0,0), spacing=0):
    widget = QFrame()
    widget.setObjectName(name)
    layout = QVBoxLayout(widget) if vertical else QHBoxLayout(widget)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return widget, layout


def tool(action, name='quiet', glyph=None, color='#526177', text=True):
    button = QToolButton()
    button.setObjectName(name)
    button.setDefaultAction(action)
    if glyph:
        action.setIcon(icon(glyph,color))
    button.setIconSize(QSize(19,19))
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon if text else Qt.ToolButtonStyle.ToolButtonIconOnly)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip(action.text() + (f'  ·  {action.shortcut().toString()}' if not action.shortcut().isEmpty() else ''))
    return button


def build_workspace(w, Canvas):
    from theme import stylesheet
    w.setStyleSheet(stylesheet('Açık'))
    root = QWidget()
    outer = QVBoxLayout(root)
    outer.setContentsMargins(0,0,0,0)
    outer.setSpacing(0)
    header, row = frame('header', margins=(24,15,22,15), spacing=12)
    logo = label('')
    logo.setPixmap(icon('file','#087f72').pixmap(30,30))
    row.addWidget(logo)
    row.addWidget(label('PDF Stüdyo','brand'))
    from version import VERSION
    row.addWidget(label(VERSION,'version'))
    row.addStretch()
    w.tools_menu = QMenu('Tüm araçlar', w)
    all_tools = QToolButton()
    all_tools.setText('Tüm araçlar')
    all_tools.setIcon(icon('grid'))
    all_tools.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    all_tools.setMenu(w.tools_menu)
    all_tools.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    row.addWidget(all_tools)
    row.addWidget(tool(w.action(root,'PDF aç',w.open,'Ctrl+O',False),glyph='open'))
    row.addWidget(tool(w.action(root,'Yeni belge',w.new,'Ctrl+N',False),glyph='plus'))
    row.addWidget(tool(w.action(root,'Kaydet',w.save,'Ctrl+S'),'primary','save','white'))
    file_menu = QMenu(w)
    w.file_menu = file_menu
    w.action(file_menu,'Farklı kaydet',lambda:w.save(True),'Ctrl+Shift+S')
    w.action(file_menu,'Yazdır',w.print_pdf,'Ctrl+P')
    more = QToolButton()
    more.setText('•••')
    more.setToolTip('Diğer dosya işlemleri')
    more.setMenu(file_menu)
    more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    row.addWidget(more)
    outer.addWidget(header)
    body, body_row = frame('body')
    sidebar, side = frame('sidebar',True,(16,22,16,18),4)
    sidebar.setFixedWidth(208)
    side.addWidget(label('DÜZENLEME ARAÇLARI','sideHeading'))
    side.addSpacing(12)
    w.mode_actions = {}
    modes = [('Gezin','cursor'),('Metni değiştir','edit'),('Metin ekle','text'),('Metni taşı','move'),
             ('Yazı stili al','style'),('İçeriği sil','erase'),('Resim ekle','image'),
             ('Resmi boyutlandır','fit'),('Vurgula','mark'),('Serbest çizim','pen'),('Çizgi','line'),('Ok','arrow'),
             ('Dikdörtgen','rect'),('Daire','circle'),('Not ekle','note'),('Bağlantı ekle','link'),('Kırp','crop')]
    for mode, glyph in modes:
        action = w.action(root,mode,lambda m=mode:w.set_mode(m))
        action.setCheckable(True)
        w.mode_actions[mode] = action
        button = tool(action,'nav',glyph,'#b4c7d9')
        button.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        side.addWidget(button)
    side.addStretch()
    side.addSpacing(12)
    side.addWidget(label('BELGE İŞLEMLERİ','sideHeading'))
    for text,fn,glyph in [('Birleştir',w.merge,'pages'),('Böl / çıkar',w.split,'file'),('Sıkıştır',w.compress,'fit')]:
        side.addWidget(tool(w.action(root,text,fn),'nav',glyph,'#b4c7d9'))
    side.addSpacing(16)
    side.addWidget(label('PDF STÜDYO  /  MASAÜSTÜ','sideFooter'))
    # Scroll on shorter displays instead of hiding tools below the window.
    scroll = QScrollArea()
    scroll.setWidget(sidebar)
    scroll.setWidgetResizable(True)
    scroll.setFixedWidth(208)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    body_row.addWidget(scroll)
    w.workspace_stack = QStackedWidget()
    body_row.addWidget(w.workspace_stack,1)
    w.workspace_stack.addWidget(build_home(w))
    editor, edit_layout = frame('editor',True)
    document_bar, docrow = frame('documentBar',margins=(24,13,18,13),spacing=12)
    w.info = label('Yeni belge','documentTitle')
    w.info.setMinimumWidth(80)
    w.info.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
    docrow.addWidget(w.info,1)
    w.search = QLineEdit()
    w.search.setPlaceholderText('Belgede ara…')
    w.search.setFixedWidth(180)
    w.search.addAction(icon('search'),QLineEdit.ActionPosition.LeadingPosition)
    w.search.returnPressed.connect(w.guarded(w.find))
    docrow.addWidget(w.search)
    w.undo_action = w.action(root,'Geri al',w.undo,'Ctrl+Z')
    w.redo_action = w.action(root,'Yinele',lambda:w.undo(True),'Ctrl+Y')
    docrow.addWidget(tool(w.undo_action,glyph='undo',text=False))
    docrow.addWidget(tool(w.redo_action,glyph='redo',text=False))
    edit_layout.addWidget(document_bar)
    w.docrow = docrow
    properties, props = frame('properties',margins=(24,8,18,8),spacing=12)
    w.mode_label = label('Gezin','modeTitle')
    props.addWidget(w.mode_label)
    props.addStretch()
    props.addWidget(label('Yazı boyutu','muted'))
    w.size = QSpinBox()
    w.size.setRange(6,120)
    w.size.setValue(16)
    w.size.setSuffix(' pt')
    w.size.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    w.size.setFixedWidth(86)
    props.addWidget(w.size)
    props.addWidget(tool(w.action(root,'Renk',w.choose_color,needs=False),glyph='style'))
    props.addSpacing(12)
    w.zoom = QSpinBox()
    w.zoom.setRange(30,300)
    w.zoom.setValue(100)
    w.zoom.setSuffix(' %')
    w.zoom.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    w.zoom.setFixedWidth(86)
    w.zoom.valueChanged.connect(lambda _:w.render())
    props.addWidget(w.zoom)
    props.addWidget(tool(w.action(root,'Genişliğe sığdır',w.fit_width),glyph='fit',text=False))
    edit_layout.addWidget(properties)
    content, content_row = frame('content')
    w.content_row = content_row
    w.canvas = Canvas()
    w.canvas.selected.connect(w.edit_selection)
    w.canvas.moved.connect(w.move_selected_text)
    content_row.addWidget(w.canvas,1)
    panel, panelcol = frame('pagePanel',True,(10,18,10,10),8)
    panel.setFixedWidth(176)
    panelcol.addWidget(label('SAYFALAR','panelHeading'))
    w.thumbs = QListWidget()
    w.thumbs.setIconSize(QSize(104,144))
    w.thumbs.setViewMode(QListWidget.ViewMode.IconMode)
    w.thumbs.setFlow(QListWidget.Flow.TopToBottom)
    w.thumbs.setWrapping(False)
    w.thumbs.setResizeMode(QListWidget.ResizeMode.Adjust)
    w.thumbs.setSpacing(3)
    w.thumbs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    w.thumbs.currentRowChanged.connect(w.select_page)
    panelcol.addWidget(w.thumbs,1)
    page_menu = QMenu(w)
    for text,fn in [('Döndür',w.rotate),('Sayfa sil',w.delete_page),('Boş sayfa ekle',w.blank),
                    ('Öne taşı',lambda:w.move(-1)),('Arkaya taşı',lambda:w.move(1)),
                    ('PNG aktar',w.export_image),('Metin aktar',w.export_text),('Parolalı kopya',w.protect),('Form doldur',w.form)]:
        w.action(page_menu,text,fn)
    page_button = QToolButton()
    page_button.setText('Sayfa işlemleri')
    page_button.setMenu(page_menu)
    page_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    page_button.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
    panelcol.addWidget(page_button)
    content_row.addWidget(panel)
    edit_layout.addWidget(content,1)
    w.workspace_stack.addWidget(editor)
    outer.addWidget(body,1)
    w.setCentralWidget(root)
    w.set_mode('Gezin')


def build_home(w):
    home, column = frame('home',True,(44,30,44,30),14)
    column.addStretch(1)
    column.addWidget(label('ÇALIŞMA ALANINIZA HOŞ GELDİNİZ','eyebrow'))
    column.addWidget(label('Belgelerinize\nyeni bir alan açın.','heroTitle'))
    description = label('Düzenleyin, birleştirin, dönüştürün.\nPDF araçlarınız tek bir yerde.','heroBody')
    column.addWidget(description)
    column.addSpacing(14)
    hero, row = frame('hero',margins=(28,26,28,26),spacing=28)
    intro = QVBoxLayout()
    intro.setSpacing(12)
    intro.addWidget(label('Bir PDF ile başlayın','paperHeading'))
    caption = label('Dosyanızı buraya sürükleyin veya\nbilgisayarınızdan bir belge seçin.','heroBody')
    intro.addWidget(caption)
    buttons = QHBoxLayout()
    open_button = QPushButton('PDF dosyası aç')
    open_button.setObjectName('primary')
    open_button.setIcon(icon('open','white'))
    open_button.clicked.connect(w.guarded(w.open))
    buttons.addWidget(open_button)
    buttons.addWidget(label('Ctrl + O','heroSmall'))
    buttons.addStretch()
    intro.addLayout(buttons)
    row.addLayout(intro,1)
    paper, papercol = frame('paper',True,(20,18,20,18),9)
    paper.setFixedSize(140,172)
    papercol.addWidget(label('PDF','paperHeading'))
    papercol.addSpacing(5)
    for width in (90,72,90,82):
        line = QFrame()
        line.setFixedSize(width,5)
        line.setObjectName('paperLine')
        papercol.addWidget(line)
    papercol.addStretch()
    papercol.addWidget(label('STÜDYO','heroSmall'))
    shadow = QGraphicsDropShadowEffect(paper)
    shadow.setBlurRadius(24)
    shadow.setOffset(0,6)
    shadow.setColor(QColor(20,65,50,25))
    paper.setGraphicsEffect(shadow)
    row.addWidget(paper)
    column.addWidget(hero)
    column.addSpacing(14)
    column.addWidget(label('HIZLI BAŞLANGIÇ','panelHeading'))
    cards = QHBoxLayout()
    cards.setSpacing(14)
    for title, subtitle, glyph, fn in [
        ('Yeni belge','Boş bir sayfayla başlayın','plus',w.new),
        ('Resimden PDF','Görsellerinizi birleştirin','image',w.from_images),
        ('Belge tara','Tarayıcıdan PDF oluşturun','scan',w.scan)]:
        card = QPushButton(f'{title}\n{subtitle}')
        card.setObjectName('card')
        card.setIcon(icon(glyph,'#087f72'))
        card.setIconSize(QSize(28,28))
        card.setMinimumHeight(96)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.clicked.connect(w.guarded(fn))
        cards.addWidget(card,1)
    column.addLayout(cards)
    column.addSpacing(8)
    column.addWidget(label('Diğer dönüştürme, güvenlik ve yapay zekâ seçenekleri: Tüm araçlar','muted'))
    column.addStretch(2)
    scroll = QScrollArea()
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setWidget(home)
    return scroll

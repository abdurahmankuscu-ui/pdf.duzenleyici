"""Light and dark palettes for the Qt stylesheet. The template names colour roles
({surface}, {text}, …) because one light colour can play several roles."""
import re

THEMES = ('Sistem', 'Açık', 'Koyu')

TEMPLATE = '''
QWidget { color:{text}; font-family:"Segoe UI"; font-size:13px; }
QMainWindow, QDialog { background:{bg}; }
QFrame#header, QFrame#documentBar, QFrame#properties { background:{surface}; border-bottom:1px solid {border}; }
QFrame#sidebar { background:{sidebar}; }
QLabel#brand { color:{title}; font-size:21px; font-weight:700; }
QLabel#version { color:{muted}; font-size:11px; }
QLabel#sideHeading { color:{side_heading}; font-size:10px; font-weight:600; letter-spacing:2px; }
QLabel#sideFooter { color:{side_footer}; font-size:11px; }
QToolButton, QPushButton { background:{surface}; border:1px solid {control_border}; border-radius:8px; padding:9px 14px; }
QToolButton:hover, QPushButton:hover { background:{hover}; border-color:{hover_border}; }
QToolButton:pressed, QPushButton:pressed { background:{pressed}; }
QToolButton:disabled, QPushButton:disabled { color:{disabled_text}; background:{disabled_bg}; border-color:{disabled_border}; }
QToolButton#primary, QPushButton#primary { background:{accent}; color:{on_accent}; border:1px solid {accent}; font-weight:600; }
QToolButton#primary:hover, QPushButton#primary:hover { background:{accent_hover}; }
QToolButton#primary:disabled { background:{accent_disabled}; color:{accent_disabled_text}; border-color:{accent_disabled}; }
QToolButton#nav { background:transparent; color:{side_text}; border:0; border-radius:7px; text-align:left; padding:9px 12px; }
QToolButton#nav:hover { background:{side_hover}; color:{side_hover_text}; }
QToolButton#nav:checked { background:{side_checked}; color:{side_checked_text}; font-weight:600; }
QToolButton#nav:disabled { color:{side_disabled}; background:transparent; }
QToolButton#quiet { background:transparent; border:0; padding:7px; }
QToolButton#quiet:hover { background:{hover}; }
QToolButton::menu-indicator { width:0; }
QFrame#pagePanel { background:{panel}; border-left:1px solid {border}; }
QLabel#panelHeading { font-weight:600; font-size:12px; color:{soft}; }
QListWidget { background:transparent; border:0; outline:0; padding:8px; }
QListWidget::item { padding:14px 6px; margin:4px 0; border:1px solid transparent; border-radius:8px; color:{item_text}; }
QListWidget::item:selected { background:{selected}; border:1px solid {selected_border}; color:{selected_text}; }
QListWidget::item:hover { background:{hover}; }
QGraphicsView { background:{canvas}; border:0; }
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QComboBox, QTableWidget { background:{surface}; border:1px solid {control_border}; border-radius:7px; padding:7px; selection-background-color:{selection}; selection-color:{selection_text}; }
QLineEdit:focus, QTextEdit:focus { border-color:{focus}; }
QSpinBox, QDoubleSpinBox { padding-right:8px; }
QHeaderView::section { background:{panel}; color:{soft}; border:0; padding:6px; }
QLabel#documentTitle { font-weight:600; color:{strong}; }
QLabel#muted { color:{muted}; font-size:12px; }
QLabel#modeTitle { color:{accent_text}; font-weight:600; }
QFrame#home { background:{bg}; }
QLabel#eyebrow { color:{accent_text}; font-weight:600; font-size:11px; letter-spacing:2px; }
QLabel#heroTitle { font-size:38px; font-weight:600; color:{title}; }
QLabel#heroBody { font-size:15px; color:{muted}; }
QFrame#hero { background:{hero}; border:1px solid {hero_border}; border-radius:18px; }
QLabel#heroSmall { color:{hero_small}; font-size:12px; }
QFrame#paper { background:{surface}; border:1px solid {paper_border}; border-radius:8px; }
QFrame#paperLine { background:{paper_line}; border-radius:2px; }
QLabel#paperHeading { font-size:18px; font-weight:700; color:{paper_heading}; }
QPushButton#card { background:{surface}; text-align:left; padding:23px; border:1px solid {card_border}; border-radius:12px; font-size:14px; }
QPushButton#card:hover { border-color:{card_hover_border}; background:{card_hover}; }
QMenu { background:{surface}; border:1px solid {control_border}; padding:7px; }
QMenu::item { padding:9px 30px 9px 14px; border-radius:5px; }
QMenu::item:selected { background:{selected}; color:{selected_text}; }
QMenu::item:disabled { color:{disabled_text}; }
QStatusBar { background:{surface}; border-top:1px solid {border}; color:{muted}; font-size:11px; padding:4px 12px; }
QStatusBar::item { border:0; }
QScrollBar:vertical { background:transparent; width:9px; margin:2px; }
QScrollBar::handle:vertical { background:{scrollbar}; border-radius:3px; min-height:30px; }
QScrollBar:horizontal { background:transparent; height:9px; margin:2px; }
QScrollBar::handle:horizontal { background:{scrollbar}; border-radius:3px; min-width:30px; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
QToolTip { background:{tooltip}; color:{tooltip_text}; border:0; padding:7px; }
'''

LIGHT = dict(
    bg='#f4f6f8', surface='#ffffff', panel='#f8fafb', border='#e5eaf0', control_border='#dfe5eb',
    text='#243348', strong='#344459', title='#172638', muted='#8190a2', soft='#526177', item_text='#69798d',
    hover='#f0f5f7', hover_border='#bac9d4', pressed='#dfeeea',
    disabled_text='#a6b0bd', disabled_bg='#f7f8fa', disabled_border='#edf0f3',
    accent='#087f72', accent_hover='#066a60', accent_text='#087f72', on_accent='#ffffff',
    accent_disabled='#e7efed', accent_disabled_text='#9eafaa',
    sidebar='#172638', side_text='#d4deea', side_hover='#25384e', side_hover_text='#ffffff',
    side_checked='#254a50', side_checked_text='#88ead3', side_disabled='#708095',
    side_heading='#7f93aa', side_footer='#8295ac',
    selected='#e1f2ed', selected_border='#8bc5b7', selected_text='#126b5a',
    canvas='#e9edf2', selection='#c5e8df', selection_text='#172638', focus='#4b9d8b',
    hero='#e7f1ee', hero_border='#d8e7e1', hero_small='#577b70',
    paper_border='#dce6e2', paper_line='#e5ecea', paper_heading='#263f40',
    card_border='#e0e7ec', card_hover_border='#72b3a3', card_hover='#f8fcfa',
    scrollbar='#bac7d2', tooltip='#172638', tooltip_text='#ffffff')

DARK = dict(
    bg='#131a22', surface='#1c2530', panel='#18212b', border='#2a3542', control_border='#34414f',
    text='#d7e0ea', strong='#e3eaf2', title='#f1f5f9', muted='#8b9aab', soft='#a3b2c2', item_text='#a3b2c2',
    hover='#26323f', hover_border='#4a5a6b', pressed='#1f3d36',
    disabled_text='#5d6b7a', disabled_bg='#1a222b', disabled_border='#252f3a',
    accent='#0d8f80', accent_hover='#10a594', accent_text='#4fd1bd', on_accent='#ffffff',
    accent_disabled='#22302d', accent_disabled_text='#5f7a74',
    sidebar='#0e141b', side_text='#c3cfdc', side_hover='#1c2835', side_hover_text='#ffffff',
    side_checked='#173a37', side_checked_text='#7fe3cf', side_disabled='#4f5d6c',
    side_heading='#6b7f95', side_footer='#6b7f95',
    selected='#1d3a33', selected_border='#2f7a69', selected_text='#8fe6d2',
    canvas='#0b1016', selection='#245247', selection_text='#f1f5f9', focus='#3fb39c',
    hero='#17302b', hero_border='#24453e', hero_small='#86b5a8',
    paper_border='#2f3d3a', paper_line='#2c3b39', paper_heading='#dbe8e4',
    card_border='#2f3b48', card_hover_border='#3f9582', card_hover='#1c2a27',
    scrollbar='#3b4958', tooltip='#0e141b', tooltip_text='#f1f5f9')

PALETTES = {'Açık': LIGHT, 'Koyu': DARK}


def resolve(choice):
    if choice in PALETTES:
        return choice
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        scheme = QGuiApplication.styleHints().colorScheme()
        return 'Koyu' if scheme == Qt.ColorScheme.Dark else 'Açık'
    except Exception:
        return 'Açık'


def stylesheet(choice='Açık'):
    palette = PALETTES[resolve(choice)]
    return re.sub(r'\{(\w+)\}', lambda m: palette[m.group(1)], TEMPLATE)

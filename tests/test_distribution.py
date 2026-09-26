import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import json
import re
import pytest


def test_version_ordering():
    from updater import parse_version
    assert parse_version('v2.10') > parse_version('2.9')
    assert parse_version('v2.4.1') > parse_version('2.4')
    assert parse_version('2.4') == parse_version('v2.4.0')
    with pytest.raises(ValueError):
        parse_version('latest')


def release(tag, url=None):
    return json.dumps({'tag_name': tag, 'name': f'PDF Stüdyo {tag}',
                       'html_url': url or f'https://github.com/abdurahmankuscu-ui/pdf.duzenleyici/releases/tag/{tag}'}).encode()


def test_check_reports_newer_release():
    from updater import check_for_update
    result = check_for_update('2.4', fetch=lambda url: release('v2.5'))
    assert result['newer'] and result['latest'] == 'v2.5'
    assert result['url'].startswith('https://github.com/abdurahmankuscu-ui/pdf.duzenleyici/releases/')
    assert not check_for_update('2.5', fetch=lambda url: release('v2.5'))['newer']


def test_check_ignores_foreign_download_links():
    from updater import check_for_update, RELEASES_PAGE
    result = check_for_update('2.4', fetch=lambda url: release('v9.9', 'https://kotu-site.example/indir.exe'))
    assert result['url'] == RELEASES_PAGE


def test_check_uses_only_the_project_api_over_https():
    from updater import check_for_update
    seen = []
    check_for_update('2.4', fetch=lambda url: seen.append(url) or release('v2.4'))
    assert seen == ['https://api.github.com/repos/abdurahmankuscu-ui/pdf.duzenleyici/releases/latest']


def test_check_without_releases():
    from updater import check_for_update, UpdateError
    def missing(url):
        raise UpdateError('yok', status=404)
    result = check_for_update('2.4', fetch=missing)
    assert not result['newer'] and result['latest'] is None


def test_palettes_define_every_role_and_dark_has_no_light_surfaces():
    from theme import stylesheet, PALETTES, TEMPLATE
    roles = set(re.findall(r'\{(\w+)\}', TEMPLATE))
    for name, palette in PALETTES.items():
        assert roles <= set(palette), (name, roles - set(palette))
    dark = stylesheet('Koyu')
    assert not re.search(r'\{\w+\}', dark)
    backgrounds = re.findall(r'background:(#[0-9a-fA-F]{6})', dark)
    # Every dark background is actually dark (low luminance).
    def luminance(c):
        r, g, b = (int(c[i:i+2], 16) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    light_backgrounds = [c for c in backgrounds if luminance(c) > 110 and c not in (PALETTES['Koyu']['accent'], PALETTES['Koyu']['accent_hover'])]
    assert not light_backgrounds
    assert 'white' not in dark


def test_theme_choice_is_applied_and_remembered(tmp_path):
    from PySide6.QtWidgets import QApplication
    from app import Window
    from theme import stylesheet
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.set_theme('Koyu')
    assert window.styleSheet() == stylesheet('Koyu')
    assert window.session.preference('theme') == 'Koyu'
    again = Window()
    again.session = window.session
    again.apply_saved_theme()
    assert again.styleSheet() == stylesheet('Koyu')
    window.close()
    again.close()


def test_single_version_everywhere():
    from PySide6.QtWidgets import QApplication
    from app import Window
    from version import VERSION
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.refresh()
    assert window.windowTitle().endswith(f'PDF Stüdyo {VERSION}')
    shown = []
    window.result_text = lambda title, text: shown.append(text)
    window.about()
    assert VERSION in shown[0] and '0.1' not in shown[0]
    window.close()


def test_installer_script_matches_version():
    from pathlib import Path
    from version import VERSION
    script = (Path(__file__).resolve().parents[1] / 'installer.iss').read_text(encoding='utf-8')
    assert f'#define AppVersion "{VERSION}"' in script
    assert 'PrivilegesRequired=lowest' in script

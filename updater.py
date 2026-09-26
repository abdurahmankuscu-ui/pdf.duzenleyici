"""Manual update check against the project's GitHub releases.

Only a version number is read. Nothing is downloaded or executed: the user is
sent to the project's release page, and only links inside that page are trusted."""
import json
import re
import urllib.error
import urllib.request

REPOSITORY = 'abdurahmankuscu-ui/pdf.duzenleyici'
API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
RELEASES_PAGE = f'https://github.com/{REPOSITORY}/releases'


class UpdateError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def parse_version(text):
    match = re.fullmatch(r'v?(\d+(?:\.\d+)*)', str(text).strip())
    if not match:
        raise ValueError(f'Sürüm numarası okunamadı: {text}')
    parts = [int(p) for p in match.group(1).split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def _fetch(url):
    request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json',
                                                   'User-Agent': 'PDF-Studyo-update-check'})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read(1_000_000)
    except urllib.error.HTTPError as exc:
        raise UpdateError(f'GitHub yanıtı: {exc.code}', status=exc.code) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateError('GitHub’a bağlanılamadı. İnternet bağlantınızı kontrol edin.') from exc


def check_for_update(current, fetch=_fetch):
    try:
        data = json.loads(fetch(API_URL))
    except UpdateError as exc:
        if exc.status == 404:
            return dict(newer=False, latest=None, url=RELEASES_PAGE, name=None)
        raise
    except ValueError as exc:
        raise UpdateError('Sürüm bilgisi okunamadı.') from exc
    tag = str(data.get('tag_name', ''))
    url = str(data.get('html_url', ''))
    # Never follow a link that points outside this project's release pages.
    if not url.startswith(RELEASES_PAGE + '/'):
        url = RELEASES_PAGE
    try:
        newer = parse_version(tag) > parse_version(current)
    except ValueError:
        newer = False
    return dict(newer=newer, latest=tag or None, url=url, name=data.get('name') or tag)

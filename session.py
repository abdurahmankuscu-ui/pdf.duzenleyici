"""Recent files and crash recovery, kept under the user's local app data folder."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import pymupdf as fitz
from engine import atomic_write

MAX_RECENT = 10


class Session:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.recovery_dir = self.folder / 'recovery'

    def _preferences(self):
        try:
            data = json.loads((self.folder / 'preferences.json').read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_preferences(self, data):
        self.folder.mkdir(parents=True, exist_ok=True)
        temporary = self.folder / 'preferences.tmp'
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, self.folder / 'preferences.json')

    def recent(self):
        entries = self._preferences().get('recent', [])
        return [p for p in entries if isinstance(p, str) and Path(p).is_file()][:MAX_RECENT]

    def add_recent(self, path):
        path = str(Path(path).resolve())
        data = self._preferences()
        data['recent'] = ([path] + [p for p in data.get('recent', []) if p != path])[:MAX_RECENT]
        self._write_preferences(data)

    def clear_recent(self):
        data = self._preferences()
        data['recent'] = []
        self._write_preferences(data)

    @staticmethod
    def _id(editor):
        # One recovery slot per document (per original path, or per unsaved window).
        return hashlib.sha256((editor.path or f'yeni-{id(editor)}').encode('utf-8')).hexdigest()[:16]

    def save_recovery(self, editor):
        """Protected documents stay encrypted with the same password; the password
        itself is never written to disk."""
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        slot = self._id(editor)
        options = dict(garbage=1, deflate=True)
        if editor.password:
            options.update(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=editor.password, user_pw=editor.password)
        atomic_write(self.recovery_dir / f'{slot}.pdf', editor.doc.tobytes(**options))
        meta = dict(id=slot, original=editor.path, protected=bool(editor.password),
                    saved=datetime.datetime.now().isoformat(timespec='seconds'))
        (self.recovery_dir / f'{slot}.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    def recoveries(self):
        entries = []
        for meta_path in sorted(self.recovery_dir.glob('*.json')):
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            pdf = meta_path.with_suffix('.pdf')
            if pdf.is_file():
                entries.append(dict(meta, file=str(pdf)))
        return entries

    def discard_recovery(self, editor=None, slot=None):
        slot = slot or self._id(editor)
        for suffix in ('.pdf', '.json'):
            try:
                (self.recovery_dir / f'{slot}{suffix}').unlink()
            except FileNotFoundError:
                pass

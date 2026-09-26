"""Discover and start local PDF Studio integrations without modifying system PATH."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

APP_DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'PDFStudyo'
OLLAMA_URL = 'http://127.0.0.1:11434'
DEFAULT_MODEL = 'qwen3:4b-instruct'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def ai_enabled():
    try:
        settings = json.loads((APP_DATA / 'preferences.json').read_text(encoding='utf-8'))
        return isinstance(settings, dict) and settings.get('ai_enabled') is True
    except (OSError, ValueError, TypeError):
        return False


def stop_managed_ollama():
    """Stop only engines installed in this application's dedicated runtime folder."""
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    service = processes = process = None
    owned = []
    root = (APP_DATA / 'ollama').resolve()
    try:
        service = win32com.client.GetObject('winmgmts:')
        processes = service.ExecQuery("SELECT ProcessId, ExecutablePath FROM Win32_Process WHERE Name='ollama.exe' OR Name='llama-server.exe'")
        for process in processes:
            if process.ExecutablePath and Path(process.ExecutablePath).resolve().is_relative_to(root):
                owned.append(int(process.ProcessId))
    finally:
        process = processes = service = None
        pythoncom.CoUninitialize()
    for pid in owned:
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                       capture_output=True, creationflags=NO_WINDOW, timeout=15)


def set_ai_enabled(enabled):
    APP_DATA.mkdir(parents=True, exist_ok=True)
    path = APP_DATA / 'preferences.json'
    try:
        settings = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(settings, dict):
            settings = {}
    except (OSError, ValueError):
        settings = {}
    settings['ai_enabled'] = bool(enabled)
    temporary = APP_DATA / 'preferences.tmp'
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)
    if not enabled:
        stop_managed_ollama()


def find_ghostscript():
    candidates = [APP_DATA / 'ghostscript' / 'bin' / 'gswin64c.exe']
    executable = shutil.which('gswin64c')
    if executable:
        candidates.append(Path(executable))
    candidates.extend(sorted(Path('C:/Program Files/gs').glob('*/bin/gswin64c.exe'), reverse=True))
    return next((p for p in candidates if p.is_file()), None)


def find_ollama():
    candidates = [APP_DATA / 'ollama' / 'ollama.exe', APP_DATA.parent / 'Programs' / 'Ollama' / 'ollama.exe']
    executable = shutil.which('ollama')
    if executable:
        candidates.append(Path(executable))
    return next((p for p in candidates if p.is_file()), None)


def find_validator():
    return next(iter(sorted((APP_DATA / 'verapdf' / 'bin').glob('cli-*.jar'))), None)


def local_json(path, data=None, timeout=5):
    """Local requests must never be routed through a configured HTTP proxy."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(OLLAMA_URL + path,
        data=json.dumps(data).encode('utf-8') if data is not None else None,
        headers={'Content-Type': 'application/json'})
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def ensure_ollama(timeout=30):
    if not ai_enabled():
        raise RuntimeError('AI kapalı. Kullanmak için Yapay zekâ menüsünden Yerel AI seçeneğini etkinleştirin.')
    try:
        return local_json('/api/tags')['models']
    except Exception:
        pass
    executable = find_ollama()
    if not executable:
        raise RuntimeError('Yerel AI motoru bulunamadı. Ollama kurulumu gerekli; Yardım > Entegrasyon durumu bölümünü açın.')
    APP_DATA.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(OLLAMA_HOST='127.0.0.1:11434', OLLAMA_MODELS=str(APP_DATA / 'models'),
               OLLAMA_NO_CLOUD='1', OLLAMA_KEEP_ALIVE='5m', OLLAMA_NUM_PARALLEL='1')
    with (APP_DATA / 'ollama-server.log').open('ab') as log:
        process = subprocess.Popen([str(executable), 'serve'], env=env, cwd=str(executable.parent),
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=NO_WINDOW)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return local_json('/api/tags', timeout=1)['models']
        except Exception:
            if process.poll() is not None:
                break
            time.sleep(0.3)
    raise RuntimeError(f'Ollama başlatılamadı. Günlük: {APP_DATA / "ollama-server.log"}')


def scanner_devices():
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    manager = info = None
    try:
        manager = win32com.client.Dispatch('WIA.DeviceManager')
        devices = []
        for info in manager.DeviceInfos:
            if info.Type == 1:
                devices.append(str(info.Properties('Name').Value))
        return devices
    finally:
        # Release COM interfaces before uninitializing the apartment.
        info = manager = None
        pythoncom.CoUninitialize()


def validate_pdfa(path):
    jar = find_validator()
    java = shutil.which('java')
    if not jar or not java:
        raise RuntimeError('PDF/A doğrulaması için veraPDF ve Java gerekli. Doğrulanmamış dosya PDF/A olarak kaydedilmedi.')
    result = subprocess.run([java, '-Dfile.encoding=UTF-8', '-jar', str(jar), '--format', 'xml',
        '--flavour', '2b', str(Path(path).resolve())], capture_output=True, timeout=180, creationflags=NO_WINDOW)
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as exc:
        raise RuntimeError('veraPDF raporu okunamadı: ' + result.stderr.decode('utf-8', errors='replace')[-1200:]) from exc
    reports = [node for node in root.iter() if node.tag.split('}')[-1] == 'validationReport']
    compliant = result.returncode == 0 and bool(reports) and all(node.get('isCompliant') == 'true' for node in reports)
    return {'compliant': compliant, 'profile': 'PDF/A-2b', 'report': result.stdout.decode('utf-8')}


def status_text():
    lines = [f'AI: {"Etkin" if ai_enabled() else "Kapalı (model çalıştırılmaz)"}',
             f'Ghostscript: {find_ghostscript() or "Kurulu değil"}',
             f'veraPDF: {find_validator() or "Kurulu değil"}',
             f'Java: {shutil.which("java") or "Kurulu değil"}',
             f'Ollama: {find_ollama() or "Kurulu değil"}']
    if ai_enabled():
        try:
            models = local_json('/api/tags', timeout=2).get('models', [])
            lines.append('Yerel AI modelleri: ' + (', '.join(m['name'] for m in models) or 'Model indirilmedi'))
        except Exception:
            lines.append('Yerel AI servisi: Çalışmıyor; AI aracı seçildiğinde başlatılır.')
    try:
        devices = scanner_devices()
        lines.append('WIA tarayıcıları: ' + (', '.join(devices) or 'Bağlı tarayıcı bulunamadı.'))
    except Exception as exc:
        lines.append('Tarayıcı denetimi başarısız: ' + str(exc))
    return '\n\n'.join(lines)

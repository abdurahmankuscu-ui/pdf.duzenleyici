import pytest
import integrations


def test_ai_disabled_by_default_does_not_contact_or_start_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, 'APP_DATA', tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail('Disabled AI must not contact or start a model server')
    monkeypatch.setattr(integrations, 'local_json', forbidden)
    monkeypatch.setattr(integrations.subprocess, 'Popen', forbidden)
    assert not integrations.ai_enabled()
    with pytest.raises(RuntimeError, match='AI kapalı'):
        integrations.ensure_ollama()


def test_setting_persists_and_disabling_stops_managed_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, 'APP_DATA', tmp_path)
    stopped = []
    monkeypatch.setattr(integrations, 'stop_managed_ollama', lambda: stopped.append(True))
    integrations.set_ai_enabled(True)
    assert integrations.ai_enabled()
    assert not stopped
    integrations.set_ai_enabled(False)
    assert not integrations.ai_enabled()
    assert stopped == [True]


@pytest.mark.parametrize('data', ['[]', 'null', '{bad', '{"ai_enabled":"true"}'])
def test_invalid_preferences_keep_ai_disabled(tmp_path, monkeypatch, data):
    monkeypatch.setattr(integrations, 'APP_DATA', tmp_path)
    (tmp_path / 'preferences.json').write_text(data)
    assert not integrations.ai_enabled()

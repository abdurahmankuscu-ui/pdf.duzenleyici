import pytest


@pytest.fixture(autouse=True)
def isolated_session(tmp_path_factory, monkeypatch):
    """Windows created in tests must not write recent files or recovery copies
    into the real %LOCALAPPDATA%\\PDFStudyo folder."""
    import workflow_ui
    from session import Session
    folder = tmp_path_factory.mktemp('appdata')
    monkeypatch.setattr(workflow_ui, 'Session', lambda _folder: Session(folder))

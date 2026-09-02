from __future__ import annotations

import pytest

from src.sandbox import Sandbox
from src.config import settings


def test_sandbox_requires_docker(monkeypatch):
    import docker

    class FakeContainers:
        def run(self, **kwargs):
            raise docker.errors.DockerException("Docker not available")

    class FakeClient:
        containers = FakeContainers()

    monkeypatch.setattr("src.sandbox.docker.from_env", lambda: FakeClient())
    with pytest.raises(docker.errors.DockerException):
        Sandbox("/tmp")


def test_sandbox_cleanup_swallows_errors(monkeypatch):
    class FakeContainer:
        def stop(self, timeout=None):
            raise RuntimeError("already stopped")

        def remove(self, force=False):
            raise RuntimeError("already removed")

    class FakeContainers:
        def run(self, *args, **kwargs):
            return FakeContainer()

    class FakeClient:
        containers = FakeContainers()

    monkeypatch.setattr("src.sandbox.docker.from_env", lambda: FakeClient())
    box = Sandbox.__new__(Sandbox)
    box.container = FakeContainer()
    box._repo_path = "/tmp"
    box._client = FakeClient()
    box.cleanup()


def test_sandbox_context_manager_calls_cleanup(monkeypatch):
    cleaned = []

    class FakeContainer:
        def exec_run(self, *a, **kw):
            class R:
                exit_code = 0
                output = (b"", b"")
            return R()

        def stop(self, timeout=None):
            cleaned.append("stop")

        def remove(self, force=False):
            cleaned.append("remove")

    class FakeContainers:
        def run(self, *a, **kw):
            return FakeContainer()

    class FakeClient:
        containers = FakeContainers()

    monkeypatch.setattr("src.sandbox.docker.from_env", lambda: FakeClient())
    with Sandbox("/tmp") as box:
        pass
    assert "stop" in cleaned
    assert "remove" in cleaned


def test_sandbox_exec_decodes_output(monkeypatch):
    class FakeContainer:
        def exec_run(self, cmd, **kwargs):
            class R:
                exit_code = 0
                output = (b"hello stdout", b"hello stderr")
            return R()

    class FakeContainers:
        def run(self, *a, **kw):
            return FakeContainer()

    class FakeClient:
        containers = FakeContainers()

    monkeypatch.setattr("src.sandbox.docker.from_env", lambda: FakeClient())
    box = Sandbox("/tmp")
    code, output = box.exec("echo hello")
    assert code == 0
    assert "hello" in output

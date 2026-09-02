from __future__ import annotations

import docker
from docker.models.containers import Container

from .config import settings


class Sandbox:
    def __init__(self, repo_path: str) -> None:
        self._client = docker.from_env()
        self._repo_path = repo_path
        self.container: Container = self._start()

    def _start(self) -> Container:
        return self._client.containers.run(
            image=settings.docker_image,
            command="sleep infinity",
            volumes={self._repo_path: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            mem_limit=settings.sandbox_memory_limit,
            cpu_period=100000,
            cpu_quota=settings.sandbox_cpu_quota,
            network_mode="none",
            detach=True,
            remove=False,
        )

    def exec(self, cmd: str, timeout: int | None = None) -> tuple[int, str]:
        effective_timeout = timeout or settings.command_timeout
        try:
            result = self.container.exec_run(
                cmd,
                demux=True,
                environment={"PYTHONPATH": "/workspace"},
            )
            stdout = result.output[0] or b""
            stderr = result.output[1] or b""
            combined = (stdout + stderr).decode("utf-8", errors="replace")
            return result.exit_code, combined
        except Exception as exc:
            return 1, str(exc)

    def install_deps(self) -> tuple[int, str]:
        return self.exec("pip install -r requirements.txt --quiet")

    def cleanup(self) -> None:
        try:
            self.container.stop(timeout=5)
            self.container.remove(force=True)
        except Exception:
            pass

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, *_: object) -> None:
        self.cleanup()

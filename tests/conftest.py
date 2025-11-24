import inspect
import os
import socket
from dataclasses import dataclass

import pytest

import manage_iocs.commands as cmds
import manage_iocs.utils


@pytest.fixture
def all_manage_iocs_commands():
    return [obj for name, obj in inspect.getmembers(cmds) if inspect.isfunction(obj)]


@pytest.fixture(autouse=True)
def sim_running_as_root(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user


@pytest.fixture
def sample_config_file_factory(tmp_path):
    def _simple_config_file(
        name: str,
        port: int = 1234,
        user: str = "softioc",
        exec_path: str = "st.cmd",
        hostname: str = "localhost",
        chdir: str | None = None,
    ):
        config_content = f"""
# Sample IOC configuration
PORT={port}
HOST={hostname}
USER={user}
EXEC={exec_path}
NAME={name}
        """
        os.makedirs(tmp_path / "iocs" / name, exist_ok=True)
        with open(tmp_path / "iocs" / name / "config", "w") as config_file:
            config_file.write(config_content)
            if chdir:
                config_file.write(f"CHDIR={chdir}\n")
        return tmp_path / "iocs" / name / "config"

    return _simple_config_file


@pytest.fixture
def sample_config_file(sample_config_file_factory):
    return sample_config_file_factory(name="sample_ioc", port=1234)


@dataclass(frozen=False)
class IOCState:
    state: str
    enabled: str


@pytest.fixture
def sample_iocs(tmp_path, sample_config_file_factory, monkeypatch):
    sample_config_file_factory(name="ioc1", port=1234, hostname="another_host")
    sample_config_file_factory(
        name="ioc2", port=2345, user="softioc-tst", hostname=socket.gethostname()
    )
    sample_config_file_factory(name="ioc3", port=3456, exec_path="start_epics", chdir="iocBoot")
    sample_config_file_factory(name="ioc4", port=6789)
    sample_config_file_factory(name="ioc5", port=7890, hostname="remote_host")
    sample_config_file_factory(name="ioc6", port=8901, hostname="random")

    monkeypatch.setattr(manage_iocs.utils, "IOC_SEARCH_PATH", [tmp_path / "iocs"])
    monkeypatch.setattr(
        manage_iocs.utils, "SYSTEMD_SERVICE_PATH", tmp_path / "etc" / "systemd" / "system"
    )

    log_dir = tmp_path / "var" / "log" / "softioc"
    monkeypatch.setattr(manage_iocs.utils, "MANAGE_IOCS_LOG_PATH", log_dir)
    os.makedirs(log_dir, exist_ok=True)

    ioc_states: dict[str, IOCState] = {}
    ioc_states["ioc1"] = IOCState("active", "enabled")
    ioc_states["ioc3"] = IOCState("active", "disabled")
    ioc_states["ioc4"] = IOCState("inactive", "disabled")
    ioc_states["ioc5"] = IOCState("inactive", "enabled")

    def dummy_systemctl_passthrough(action: str, ioc: str) -> tuple[str, str, int]:
        """Dummy systemctl passthrough for testing."""
        stdout = ""
        stderr = ""
        rc = 0

        if ioc not in ioc_states and action != "install":
            rc = 4  # simulating 'not found' return code
        elif action == "install" and ioc in ioc_states:
            rc = 1  # simulating 'already installed' error
        elif action == "install":
            ioc_states[ioc] = IOCState(state="stopped", enabled="disabled")
        else:
            ioc_state = ioc_states[ioc]
            if action == "is-active":
                stdout = ioc_state.state
            elif action == "is-enabled":
                stdout = ioc_state.enabled
            elif action == "uninstall":
                del ioc_states[ioc]
                os.remove(manage_iocs.utils.SYSTEMD_SERVICE_PATH / f"softioc-{ioc}.service")
            elif action == "start":
                ioc_states[ioc].state = "active"
            elif action == "stop":
                ioc_states[ioc].state = "inactive"
            elif action == "restart":
                ioc_states[ioc].state = "active"
            elif action == "enable":
                ioc_states[ioc].enabled = "enabled"
            elif action == "disable":
                ioc_states[ioc].enabled = "disabled"

        return stdout, stderr, rc

    monkeypatch.setattr(manage_iocs.utils, "systemctl_passthrough", dummy_systemctl_passthrough)

    os.makedirs(manage_iocs.utils.SYSTEMD_SERVICE_PATH, exist_ok=True)
    for ioc in ["ioc1", "ioc3", "ioc4", "ioc5"]:
        service_file = manage_iocs.utils.SYSTEMD_SERVICE_PATH / f"softioc-{ioc}.service"
        with open(service_file, "w") as f:
            f.write(f"# Dummy service file for {ioc}\n")

    return tmp_path


@pytest.fixture
def dummy_popen(monkeypatch):
    class DummyPopen:
        def __init__(self, args, stdin, stdout):
            self.args = args
            self.returncode = 0

        def wait(self):
            return self.args

        def communicate(self):
            return (str(self.args).encode(), b"")

    monkeypatch.setattr(cmds, "Popen", DummyPopen)
    monkeypatch.setattr(manage_iocs.utils, "Popen", DummyPopen)

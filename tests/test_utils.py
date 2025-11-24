import socket

import pytest

import manage_iocs.utils
from manage_iocs.utils import (
    find_installed_iocs,
    find_iocs,
    find_iocs_on_host,
    get_ioc_procserv_port,
    get_ioc_status,
    read_config_file,
    systemctl_passthrough,
)


def test_read_config_file(sample_config_file):
    config = read_config_file(sample_config_file)
    assert config["PORT"] == "1234"
    assert config["HOST"] == "localhost"
    assert config["USER"] == "softioc"
    assert config["EXEC"] == "st.cmd"
    assert config["NAME"] == "sample_ioc"


def test_find_iocs(sample_iocs):
    iocs = find_iocs()
    assert len(iocs) == 6
    assert "ioc1" in iocs
    assert "ioc2" in iocs
    assert "ioc3" in iocs
    assert iocs["ioc1"].procserv_port == 1234
    assert iocs["ioc2"].procserv_port == 2345
    assert iocs["ioc3"].procserv_port == 3456
    assert iocs["ioc2"].user == "softioc-tst"
    assert iocs["ioc3"].exec_path == "start_epics"
    assert iocs["ioc3"].chdir == "iocBoot"
    assert iocs["ioc1"].host == "another_host"
    assert iocs["ioc2"].host == socket.gethostname()
    assert iocs["ioc3"].host == "localhost"


def test_find_iocs_on_host(sample_iocs):
    iocs = find_iocs_on_host()
    assert len(iocs) == 3
    assert "ioc2" in iocs
    assert "ioc3" in iocs
    assert "ioc4" in iocs


def test_get_ioc_procserv_port(sample_iocs):
    port = get_ioc_procserv_port("ioc2")
    assert port == 2345


def test_find_installed_iocs(sample_iocs):
    iocs = find_installed_iocs()
    assert len(iocs) == 4
    assert "ioc1" in iocs
    assert "ioc3" in iocs
    assert "ioc4" in iocs
    assert "ioc5" in iocs


def test_get_ioc_status(sample_iocs):
    assert get_ioc_status("ioc1") == ("Running", True)


def test_get_ioc_status_not_installed(sample_iocs):
    with pytest.raises(RuntimeError):
        get_ioc_status("ioc2")


def test_get_ioc_status_unknown_response(sample_iocs, monkeypatch):
    def dummy_systemctl_passthrough(action: str, ioc: str) -> tuple[str, str, int]:
        if action == "is-active":
            return ("unknown response", "", 3)
        elif action == "is-enabled":
            return ("disabled", "", 3)
        else:
            return ("", "", 0)

    monkeypatch.setattr(manage_iocs.utils, "systemctl_passthrough", dummy_systemctl_passthrough)

    assert get_ioc_status("ioc1") == ("Unknown response", False)


@pytest.mark.parametrize(
    "action,ioc",
    [
        ("start", "ioc4"),
        ("stop", "ioc1"),
        ("enable", "ioc4"),
        ("disable", "ioc1"),
    ],
)
def test_systemctl_passthrough(dummy_popen, action, ioc):
    out, _, _ = systemctl_passthrough(action, ioc)
    assert out == f"['systemctl', '{action}', 'softioc-{ioc}.service']"

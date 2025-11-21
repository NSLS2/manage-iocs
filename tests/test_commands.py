import os

import pytest

import manage_iocs
import manage_iocs.commands as cmds
import manage_iocs.utils
from manage_iocs.utils import find_installed_iocs, get_ioc_status


def strip_ansi_codes(s: str) -> str:
    import re

    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", s)


def test_version(capsys):
    from manage_iocs import __version__

    assert __version__ is not None
    rc = cmds.version()
    captured = capsys.readouterr()
    assert __version__ in captured.out
    assert rc == 0


def test_help(capsys, all_manage_iocs_commands):
    rc = cmds.help()
    captured = capsys.readouterr()
    assert "Usage: manage-iocs <command> [ioc]" in captured.out
    for cmd in all_manage_iocs_commands:
        assert cmd.__name__ in captured.out
    assert rc == 0


def test_report(sample_iocs, capsys):
    cmds.report()
    captured = capsys.readouterr()
    expected_output = f"""
BASE | IOC | USER | PORT | EXEC
{sample_iocs}/iocs/ioc2 | ioc2 | softioc-tst | 2345 | {sample_iocs}/iocs/ioc2/st.cmd
{sample_iocs}/iocs/ioc3 | ioc3 | softioc | 3456 | {sample_iocs}/iocs/ioc3/iocBoot/start_epics
{sample_iocs}/iocs/ioc4 | ioc4 | softioc | 6789 | {sample_iocs}/iocs/ioc4/st.cmd
"""

    def normalize_whitespace(s: str) -> str:
        return "\n".join(" ".join(line.split()) for line in s.strip().splitlines())

    for line in expected_output.strip().splitlines():
        assert normalize_whitespace(line) in normalize_whitespace(captured.out)


@pytest.mark.parametrize(
    "ioc_name, command, before_state, before_enabled, after_state, after_enabled",
    [
        ("ioc1", cmds.stop, "Running", True, "Stopped", True),
        ("ioc3", cmds.stop, "Running", False, "Stopped", False),
        ("ioc4", cmds.stop, "Stopped", False, "Stopped", False),
        ("ioc1", cmds.start, "Running", True, "Running", True),
        ("ioc3", cmds.start, "Running", False, "Running", False),
        ("ioc4", cmds.start, "Stopped", False, "Running", False),
        ("ioc3", cmds.enable, "Running", False, "Running", True),
        ("ioc4", cmds.enable, "Stopped", False, "Stopped", True),
        ("ioc1", cmds.disable, "Running", True, "Running", False),
        ("ioc3", cmds.disable, "Running", False, "Running", False),
        ("ioc1", cmds.restart, "Running", True, "Running", True),
        ("ioc4", cmds.restart, "Stopped", False, "Running", False),
        ("ioc3", cmds.restart, "Running", False, "Running", False),
    ],
)
def test_state_change_commands(
    sample_iocs, ioc_name, command, before_state, before_enabled, after_state, after_enabled
):
    assert get_ioc_status(ioc_name) == (before_state, before_enabled)

    rc = command(ioc_name)
    assert rc == 0

    assert get_ioc_status(ioc_name) == (after_state, after_enabled)


def test_install_new_ioc(sample_iocs, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user

    assert "ioc2" not in find_installed_iocs()

    rc = cmds.install("ioc2")
    assert rc == 0

    assert get_ioc_status("ioc2") == ("Stopped", False)

    assert "ioc2" in find_installed_iocs()


def test_install_ioc_not_root(sample_iocs, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    with pytest.raises(RuntimeError, match="You must be root to install an IOC!"):
        cmds.install("ioc3")


def test_install_ioc_wrong_host(sample_iocs, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user

    with pytest.raises(RuntimeError, match="Cannot install IOC 'ioc1' on this host"):
        cmds.install("ioc1")


def test_install_already_installed_ioc(sample_iocs, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user

    assert "ioc3" in find_installed_iocs()

    with pytest.raises(RuntimeError, match="Failed to install IOC 'ioc3'!"):
        cmds.install("ioc3")


def test_uninstall_ioc(sample_iocs, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user

    assert "ioc5" in find_installed_iocs()

    rc = cmds.uninstall("ioc5")
    assert rc == 0

    assert "ioc5" not in find_installed_iocs()


def test_uninstall_ioc_not_root(sample_iocs, monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    with pytest.raises(RuntimeError, match="You must be root to uninstall an IOC!"):
        cmds.uninstall("ioc1")


@pytest.mark.parametrize(
    "cmd, expected_state, expected_enabled",
    [
        (cmds.startall, "Running", None),
        (cmds.stopall, "Stopped", None),
        (cmds.enableall, None, True),
        (cmds.disableall, None, False),
    ],
)
def test_state_change_all(sample_iocs, cmd, expected_state, expected_enabled):
    installed_iocs = find_installed_iocs()
    assert len(installed_iocs) == 4

    # Now start all
    rc = cmd()
    assert rc == 0

    # Check all are running
    for ioc in installed_iocs.values():
        if expected_state is not None:
            assert get_ioc_status(ioc.name)[0] == expected_state
        if expected_enabled is not None:
            assert get_ioc_status(ioc.name)[1] is expected_enabled


def test_attach(sample_iocs, monkeypatch, dummy_popen):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    ret = cmds.attach("ioc3")

    assert ret == ["telnet", "localhost", "3456"]


def test_status(sample_iocs, capsys):
    rc = cmds.status()
    captured = capsys.readouterr()
    expected_output = """IOC Status Auto-Start
--------------------------
ioc1 Running Enabled
ioc3 Running Disabled
ioc4 Stopped Disabled
ioc5 Stopped Enabled
"""

    def normalize_whitespace_and_ansi_codes(s: str) -> str:
        whitespace_normalized = "\n".join(" ".join(line.split()) for line in s.strip().splitlines())
        return strip_ansi_codes(whitespace_normalized)

    for line in expected_output.strip().splitlines():
        assert normalize_whitespace_and_ansi_codes(line) in normalize_whitespace_and_ansi_codes(
            captured.out
        )

    assert rc == 0


@pytest.mark.parametrize(
    "cmd, expected_message",
    [
        (cmds.start, "Failed to start IOC 'ioc4'!"),
        (cmds.stop, "Failed to stop IOC 'ioc4'!"),
        (cmds.restart, "Failed to restart IOC 'ioc4'!"),
        (cmds.enable, "Failed to enable autostart for IOC 'ioc4'!"),
        (cmds.disable, "Failed to disable autostart for IOC 'ioc4'!"),
    ],
)
def test_command_failures(sample_iocs, monkeypatch, cmd, expected_message):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user

    def failing_systemctl_passthrough(action: str, ioc: str) -> tuple[str, str, int]:
        return ("", "Simulated failure", 1)

    monkeypatch.setattr(manage_iocs.utils, "systemctl_passthrough", failing_systemctl_passthrough)

    with pytest.raises(RuntimeError, match=expected_message):
        cmd("ioc4")


@pytest.mark.parametrize(
    "failed_action, expected_message",
    [
        ("stop", "Failed to stop IOC 'ioc5' before uninstalling!"),
        ("disable", "Failed to disable IOC 'ioc5' before uninstalling!"),
        ("uninstall", "Failed to uninstall IOC 'ioc5'!"),
    ],
)
def test_uninstall_failures(sample_iocs, monkeypatch, failed_action, expected_message):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user

    def failing_systemctl_passthrough(action: str, ioc: str) -> tuple[str, str, int]:
        if action == failed_action:
            return ("", "Simulated failure", 1)
        return ("", "", 0)

    monkeypatch.setattr(manage_iocs.utils, "systemctl_passthrough", failing_systemctl_passthrough)

    with pytest.raises(RuntimeError, match=expected_message):
        cmds.uninstall("ioc5")


def test_fail_to_install_ioc_to_run_as_root(sample_iocs, monkeypatch, sample_config_file_factory):
    monkeypatch.setattr(os, "geteuid", lambda: 0)  # Mock as root user

    sample_config_file_factory(name="ioc1", user="root")
    with pytest.raises(RuntimeError, match="Refusing to install IOC 'ioc1' to run as user 'root'!"):
        cmds.install("ioc1")

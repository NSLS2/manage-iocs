import os

import pytest

import manage_iocs
import manage_iocs.commands as cmds
import manage_iocs.utils
from manage_iocs.utils import find_installed_iocs, get_ioc_statuses


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
    "ioc_name, command, before_state, before_enabled, after_state, after_enabled, as_root",
    [
        ("ioc1", cmds.stop, "Running", "Enabled", "Stopped", "Enabled", False),
        ("ioc3", cmds.stop, "Running", "Disabled", "Stopped", "Disabled", False),
        ("ioc4", cmds.stop, "Stopped", "Disabled", "Stopped", "Disabled", False),
        ("ioc1", cmds.start, "Running", "Enabled", "Running", "Enabled", False),
        ("ioc3", cmds.start, "Running", "Disabled", "Running", "Disabled", False),
        ("ioc4", cmds.start, "Stopped", "Disabled", "Running", "Disabled", False),
        ("ioc3", cmds.enable, "Running", "Disabled", "Running", "Enabled", True),
        ("ioc4", cmds.enable, "Stopped", "Disabled", "Stopped", "Enabled", True),
        ("ioc1", cmds.disable, "Running", "Enabled", "Running", "Disabled", True),
        ("ioc3", cmds.disable, "Running", "Disabled", "Running", "Disabled", True),
        ("ioc1", cmds.restart, "Running", "Enabled", "Running", "Enabled", False),
        ("ioc4", cmds.restart, "Stopped", "Disabled", "Running", "Disabled", False),
        ("ioc3", cmds.restart, "Running", "Disabled", "Running", "Disabled", False),
    ],
)
def test_state_change_commands(
    sample_iocs,
    ioc_name,
    command,
    before_state,
    before_enabled,
    after_state,
    after_enabled,
    as_root,
    monkeypatch,
):
    if not as_root:
        monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    _, status = get_ioc_statuses(ioc_name)
    assert status == (before_state, before_enabled)

    rc = command(ioc_name)
    assert rc == 0

    _, status = get_ioc_statuses(ioc_name)
    assert status == (after_state, after_enabled)


def test_install_new_ioc(sample_iocs, monkeypatch):
    assert "ioc2" not in find_installed_iocs()

    rc = cmds.install("ioc2")
    assert rc == 0

    _, status = get_ioc_statuses("ioc2")
    assert status == ("Stopped", "Disabled")

    assert "ioc2" in find_installed_iocs()


def test_install_ioc_wrong_host(sample_iocs, monkeypatch):
    with pytest.raises(RuntimeError, match="Cannot install IOC 'ioc1' on this host"):
        cmds.install("ioc1")


def test_install_already_installed_ioc(sample_iocs, monkeypatch):
    assert "ioc3" in find_installed_iocs()

    with pytest.raises(RuntimeError, match="Failed to install IOC 'ioc3'!"):
        cmds.install("ioc3")


def test_uninstall_ioc(sample_iocs, monkeypatch):
    assert "ioc5" in find_installed_iocs()

    rc = cmds.uninstall("ioc5")
    assert rc == 0

    assert "ioc5" not in find_installed_iocs()


@pytest.mark.parametrize(
    "command",
    [cmds.enable, cmds.disable, cmds.enableall, cmds.disableall, cmds.install, cmds.uninstall],
)
def test_requires_root(sample_iocs, monkeypatch, command):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    with pytest.raises(PermissionError, match="requires root privileges."):
        command("ioc1")


@pytest.mark.parametrize(
    "cmd, expected_state, expected_enabled",
    [
        (cmds.startall, "Running", None),
        (cmds.stopall, "Stopped", None),
        (cmds.enableall, None, "Enabled"),
        (cmds.disableall, None, "Disabled"),
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
            assert get_ioc_statuses(ioc.name)[1][0] == expected_state
        if expected_enabled is not None:
            assert get_ioc_statuses(ioc.name)[1][1] == expected_enabled


@pytest.mark.parametrize("as_root", [True, False])
def test_attach(sample_iocs, monkeypatch, dummy_popen, as_root):
    if not as_root:
        monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    ret = cmds.attach("ioc3")

    assert ret == ["telnet", "localhost", "3456"]


@pytest.mark.parametrize("as_root", [True, False])
def test_status(sample_iocs, capsys, monkeypatch, as_root):
    if not as_root:
        monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    rc = cmds.status()
    captured = capsys.readouterr()
    expected_output = """IOC Status Auto-Start
----------------------------
ioc1 Running Enabled
ioc3 Running Disabled
ioc4 Stopped Disabled
ioc5 Stopped Enabled
"""

    def normalize_whitespace(s: str) -> str:
        return "\n".join(" ".join(line.split()) for line in s.strip().splitlines())

    for line in expected_output.strip().splitlines():
        assert normalize_whitespace(line) in normalize_whitespace(captured.out)

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
    def failing_systemctl_passthrough(action: str, ioc: str) -> tuple[str, str, int]:
        if action == failed_action:
            return ("", "Simulated failure", 1)
        return ("", "", 0)

    monkeypatch.setattr(manage_iocs.utils, "systemctl_passthrough", failing_systemctl_passthrough)

    with pytest.raises(RuntimeError, match=expected_message):
        cmds.uninstall("ioc5")


def test_fail_to_install_ioc_to_run_as_root(sample_iocs, monkeypatch, sample_config_file_factory):
    sample_config_file_factory(name="ioc1", user="root")
    with pytest.raises(RuntimeError, match="Refusing to install IOC 'ioc1' to run as user 'root'!"):
        cmds.install("ioc1")

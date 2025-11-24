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
    assert "Usage: manage-iocs [command] <ioc>" in captured.out
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


def test_report_no_iocs(monkeypatch, capsys):
    monkeypatch.setattr(
        manage_iocs.utils,
        "find_iocs",
        lambda: {},
    )

    rc = cmds.report()
    captured = capsys.readouterr()
    assert "No IOCs found on configured to run on this host." in captured.out
    assert rc == 1


@pytest.mark.parametrize(
    "ioc_name, command, before_state, before_enabled, after_state, after_enabled, as_root",
    [
        ("ioc1", cmds.stop, "Running", True, "Stopped", True, False),
        ("ioc3", cmds.stop, "Running", False, "Stopped", False, False),
        ("ioc4", cmds.stop, "Stopped", False, "Stopped", False, False),
        ("ioc1", cmds.start, "Running", True, "Running", True, False),
        ("ioc3", cmds.start, "Running", False, "Running", False, False),
        ("ioc4", cmds.start, "Stopped", False, "Running", False, False),
        ("ioc3", cmds.enable, "Running", False, "Running", True, True),
        ("ioc4", cmds.enable, "Stopped", False, "Stopped", True, True),
        ("ioc1", cmds.disable, "Running", True, "Running", False, True),
        ("ioc3", cmds.disable, "Running", False, "Running", False, True),
        ("ioc1", cmds.restart, "Running", True, "Running", True, False),
        ("ioc4", cmds.restart, "Stopped", False, "Running", False, False),
        ("ioc3", cmds.restart, "Running", False, "Running", False, False),
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

    assert get_ioc_status(ioc_name) == (before_state, before_enabled)

    rc = command(ioc_name)
    assert rc == 0

    assert get_ioc_status(ioc_name) == (after_state, after_enabled)


def test_install_new_ioc(sample_iocs, monkeypatch):
    assert "ioc2" not in find_installed_iocs()

    rc = cmds.install("ioc2")
    assert rc == 0

    assert get_ioc_status("ioc2") == ("Stopped", False)

    assert "ioc2" in find_installed_iocs()


def test_install_ioc_wrong_host(sample_iocs, monkeypatch):
    with pytest.raises(RuntimeError, match="Cannot install IOC 'ioc6' on this host"):
        cmds.install("ioc6")


def test_install_already_installed_ioc(sample_iocs, monkeypatch):
    assert "ioc3" in find_installed_iocs()

    with pytest.raises(RuntimeError, match="IOC 'ioc3' is already installed!"):
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


@pytest.mark.parametrize("as_root", [True, False])
def test_attach(sample_iocs, monkeypatch, dummy_popen, as_root):
    if not as_root:
        monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

    ret = cmds.attach("ioc3")

    assert ret == ["telnet", "localhost", "3456"]

    with pytest.raises(RuntimeError, match="Cannot attach to IOC 'ioc4': IOC is not running!"):
        cmds.attach("ioc4")  # IOC is stopped


@pytest.mark.parametrize("as_root", [True, False])
def test_status(sample_iocs, capsys, monkeypatch, as_root):
    if not as_root:
        monkeypatch.setattr(os, "geteuid", lambda: 1000)  # Mock as non-root user

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


def test_status_no_installed_iocs(sample_iocs, monkeypatch, capsys):
    monkeypatch.setattr(
        manage_iocs.utils,
        "find_installed_iocs",
        lambda: {},
    )

    rc = cmds.status()
    captured = capsys.readouterr()
    assert "No Installed IOCs found on this host." in captured.out
    assert rc == 1


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
    sample_config_file_factory(name="ioc7", user="root", port=9012)
    with pytest.raises(RuntimeError, match="Refusing to install IOC 'ioc7' to run as user 'root'!"):
        cmds.install("ioc7")


@pytest.mark.parametrize(
    "cmd",
    [cmds.start, cmds.stop, cmds.restart, cmds.enable, cmds.disable, cmds.attach],
)
def test_command_requires_ioc_installed(sample_iocs, cmd):
    with pytest.raises(RuntimeError, match="No IOC with name 'ioc2' is installed!"):
        cmd("ioc2")


def test_nextport(sample_iocs, capsys):
    rc = cmds.nextport()
    captured = capsys.readouterr()
    assert int(captured.out.strip()) == 8902  # Highest used port is 7890 in sample_iocs
    assert rc == 0


def test_lastlog(sample_iocs, monkeypatch, capsys):
    log_file = sample_iocs / "var" / "log" / "softioc" / "ioc3.log"

    with open(log_file, "w") as f:
        f.write("Line 1\nLine 2\nLine 3\n")
        f.write('@@@ Restarting child "ioc3"\n')
        f.write("Line 4\nLine 5\n")

    rc = cmds.lastlog("ioc3")
    captured = capsys.readouterr()
    assert captured.out.strip() == '@@@ Restarting child "ioc3"\nLine 4\nLine 5'
    assert rc == 0


def test_lastlog_no_log_file(sample_iocs, monkeypatch):
    with pytest.raises(RuntimeError, match="No log file found for IOC 'ioc4'"):
        cmds.lastlog("ioc4")


def test_lastlog_no_restart_marker(sample_iocs, monkeypatch, capsys):
    log_file = sample_iocs / "var" / "log" / "softioc" / "ioc4.log"
    with open(log_file, "w") as f:
        f.write("Line A\nLine B\nLine C\n")

    rc = cmds.lastlog("ioc4")
    captured = capsys.readouterr()
    assert captured.out.strip() == "Line A\nLine B\nLine C"
    assert rc == 0

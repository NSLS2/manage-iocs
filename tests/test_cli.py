import inspect
from collections.abc import Callable

import pytest

import manage_iocs.commands as cmds
from manage_iocs.__main__ import get_command_from_args


def test_no_command_provided():
    with pytest.raises(RuntimeError, match="No command provided!"):
        get_command_from_args(["manage_iocs"])


def test_unknown_command():
    with pytest.raises(RuntimeError, match="Unknown command: unknown_cmd"):
        get_command_from_args(["manage_iocs", "unknown_cmd"])


def _get_cmds_w_required_args():
    """
    Returns a list of command names in the cmds module that require additional arguments.
    """
    cmds_w_req_args = []
    for name, obj in inspect.getmembers(cmds):
        if inspect.isfunction(obj) and bool(inspect.signature(obj).parameters):
            cmds_w_req_args.append(name)
    return cmds_w_req_args


CMDS_WITH_REQUIRED_ARGS = _get_cmds_w_required_args()


@pytest.mark.parametrize("cmd", list(CMDS_WITH_REQUIRED_ARGS))
def test_command_requires_additional_arguments(cmd):
    with pytest.raises(RuntimeError, match=f"Command '{cmd}' requires additional arguments!"):
        get_command_from_args(["manage_iocs", cmd])  # '{cmd}' requires an argument


@pytest.mark.parametrize(
    "args, expected_command",
    [
        (["attach", "ioc1"], cmds.attach),
        (["help"], cmds.help),
        (["report"], cmds.report),
        (["version"], cmds.version),
        (["status"], cmds.status),
        (["start", "ioc2"], cmds.start),
        (["stop", "ioc3"], cmds.stop),
        (["restart", "ioc4"], cmds.restart),
        (["enable", "ioc5"], cmds.enable),
        (["disable", "ioc6"], cmds.disable),
        (["startall"], cmds.startall),
        (["stopall"], cmds.stopall),
        (["install", "ioc7"], cmds.install),
        (["uninstall", "ioc8"], cmds.uninstall),
    ],
)
def test_get_command_from_args(args, expected_command):
    cmd = get_command_from_args(["manage_iocs"] + args)
    assert isinstance(cmd, Callable)
    assert cmd.__name__ == expected_command.__name__

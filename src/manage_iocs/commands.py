
from dataclasses import dataclass
from typing import Callable

from . import __version__

@dataclass
class CommandInfo:
    name: str
    description: str
    callable: Callable
    requires_root: bool = False
    requires_ioc_target: bool = False


# TODO: Add actual callable implementations
def placeholder_callable():
    pass

def print_command_descs():
    """Display help message with available commands."""
    print("Available commands:")
    for cmd_name, cmd_info in COMMANDS.items():
        print(f"  {cmd_name}: {cmd_info.description}")


COMMANDS: dict[str, CommandInfo] = {
    "help": CommandInfo(
        name="help",
        description="Display this message",
        callable=print_command_descs,
        requires_root=False,
        requires_ioc_target=False
    ),
    "report": CommandInfo(
        name="report",
        description="Show config(s) of an IOC/all IOCs on localhost",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=True
    ),
    "attach": CommandInfo(
        name="attach",
        description="Connect to procServ telnet server for IOC",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=True
    ),
    "status": CommandInfo(
        name="status",
        description="Check if installed IOCs are running or stopped",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=False
    ),
    "started": CommandInfo(
        name="started",
        description="List IOCs that are started",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=False
    ),
    "stopped": CommandInfo(
        name="stopped",
        description="List IOCs that are stopped",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=False
    ),
    "lastlog": CommandInfo(
        name="lastlog",
        description="Display the output of the last IOC startup",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=True
    ),
    "nextport": CommandInfo(
        name="nextport",
        description="Find the next unused procServ port",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=False
    ),
    "install": CommandInfo(
        name="install",
        description="Create /etc/systemd/system/softioc-[ioc].service",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "uninstall": CommandInfo(
        name="uninstall",
        description="Remove /etc/systemd/system/softioc-[ioc].service",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "start": CommandInfo(
        name="start",
        description="Start the IOC <ioc>",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "stop": CommandInfo(
        name="stop",
        description="Stop the IOC <ioc>",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "restart": CommandInfo(
        name="restart",
        description="Restart the IOC <ioc>",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "startall": CommandInfo(
        name="startall",
        description="Start all IOCs installed for this system",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=False
    ),
    "stopall": CommandInfo(
        name="stopall",
        description="Stop all IOCs installed for this system",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=False
    ),
    "enable": CommandInfo(
        name="enable",
        description="Enable auto-start IOC <ioc> at boot",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "enableall": CommandInfo(
        name="enableall",
        description="Enable auto-start for all IOCs at boot",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=False
    ),
    "disable": CommandInfo(
        name="disable",
        description="Disable auto-start IOC <ioc> at boot",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "disableall": CommandInfo(
        name="disableall",
        description="Disable auto-start for all IOCs at boot",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=False
    ),
    "list": CommandInfo(
        name="list",
        description="A list of all IOC instances under /epics/iocs:/opt/epics/iocs; including those IOCs running on other hosts",
        callable=placeholder_callable,
        requires_root=False,
        requires_ioc_target=False
    ),
    "rename": CommandInfo(
        name="rename",
        description="Rename <ioc> to <name>. Changes folder name, re-installs.",
        callable=placeholder_callable,
        requires_root=True,
        requires_ioc_target=True
    ),
    "version": CommandInfo(
        name="version",
        description="version number",
        callable=lambda: print(f"manage_iocs version {__version__}"),
        requires_root=False,
        requires_ioc_target=False
    ),
}



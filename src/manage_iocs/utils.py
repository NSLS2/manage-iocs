import os
import socket
from dataclasses import dataclass
from pathlib import Path
from subprocess import PIPE, Popen

IOC_SEARCH_PATHS = [Path("/epics/iocs"), Path("/opt/epics/iocs"), Path("/opt/iocs")]


@dataclass
class IOC:
    name: str
    user: str
    procserv_port: int
    path: Path
    host: str
    exec_path: str


def read_config_file(config_path: Path) -> dict[str, str]:
    """Read config file for IOC"""
    config: dict[str, str] = {}
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def find_iocs() -> dict[str, IOC]:
    """Get a list of IOCs available in the search paths."""
    iocs = {}
    for search_path in IOC_SEARCH_PATHS:
        for item in os.listdir(search_path):
            if os.path.isdir(search_path / item) and os.path.exists(search_path / item / "config"):
                iocs[item] = IOC(
                    name=item,
                    procserv_port=int(read_config_file(search_path / item / "config")["PORT"]),
                    path=search_path / item,
                    host=read_config_file(search_path / item / "config").get("HOST", "localhost"),
                    user=read_config_file(search_path / item / "config").get("USER", "iocuser"),
                    exec_path=read_config_file(search_path / item / "config").get("EXEC", "st.cmd"),
                )
    return iocs


def find_iocs_on_host() -> dict[str, IOC]:
    """Get a list of IOCs available on the given host."""
    all_iocs = find_iocs()
    return {
        name: ioc
        for name, ioc in all_iocs.items()
        if ioc.host == socket.gethostname() or ioc.host == "localhost"
    }


def find_installed_iocs() -> dict[str, IOC]:
    """Get a list of IOCs that have systemd service files installed."""
    iocs = {}
    for ioc in find_iocs().values():
        service_file = Path(f"/etc/systemd/system/softioc-{ioc.name}.service")
        if service_file.exists():
            iocs[ioc.name] = ioc
    return iocs


def get_ioc_procserv_port(ioc: str) -> int:
    """Get the procServ port number for the given IOC."""

    return find_iocs()[ioc].procserv_port


def systemctl_passthrough(action: str, ioc: str):
    """Helper to call systemctl with the given action and IOC name."""
    proc = Popen(["systemctl", action, f"softioc-{ioc}.service"], stdin=PIPE, stdout=PIPE)
    return proc.wait()


def get_ioc_statuses(ioc_name: str) -> tuple[int, tuple[str, str]]:
    """Get the active and enabled status of the given IOC."""

    ret = 0
    proc = Popen(
        ["systemctl", "is-active", f"softioc-{ioc_name}.service"],
        stdin=PIPE,
        stdout=PIPE,
    )
    status, _ = proc.communicate()
    status_str = status.decode().strip()
    if status_str == "inactive":
        status_str = "Stopped"
    elif status_str == "active":
        status_str = "Running"
    else:
        status_str = status_str.capitalize()
    ret += proc.returncode

    proc = Popen(
        ["systemctl", "is-enabled", f"softioc-{ioc_name}.service"],
        stdin=PIPE,
        stdout=PIPE,
    )
    enabled, _ = proc.communicate()
    enabled_str = enabled.decode().strip()
    ret += proc.returncode

    return ret, (status_str, enabled_str)

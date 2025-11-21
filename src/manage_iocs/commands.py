import inspect
import os
import socket
import sys
import time as ttime
from subprocess import PIPE, Popen

from . import __version__, utils

EXTRA_PAD_WIDTH = 5

# Length added to string to account for ANSI color escape codes
ANSI_COLOR_ESC_CODE_LEN = 9


def version():
    """Print the version of the manage-iocs package."""

    print(f"Version: {__version__}")
    return 0


def help():
    """Display this help message."""
    version()
    print("Usage: manage-iocs <command> [ioc]")
    print("Available commands:")
    docs: dict[str, str] = {}
    signatures: dict[str, list[str]] = {}
    for func in inspect.getmembers(sys.modules[__name__], inspect.isfunction):
        docs[func[0]] = str(func[1].__doc__)
        signatures[func[0]] = list(inspect.signature(func[1]).parameters.keys())

    usages = [
        f"  {name} " + " ".join(f"<{param}>" for param in params)
        for name, params in signatures.items()
    ]
    max_sig_len = max(len(sig) for sig in usages)

    for usage, doc in zip(usages, docs.values(), strict=False):
        print(f"  {usage.ljust(max_sig_len + EXTRA_PAD_WIDTH)} - {doc}")
    return 0


def attach(ioc: str):
    """Connect to procServ telnet server for the given IOC."""

    proc = Popen(
        ["telnet", "localhost", str(utils.get_ioc_procserv_port(ioc))],
        stdin=PIPE,
        stdout=PIPE,
    )
    return proc.wait()


def report():
    """Show config(s) of an all IOCs on localhost"""
    base_hostname = socket.gethostname()
    if "." in base_hostname:
        base_hostname = base_hostname.split(".")[0]

    iocs = [
        ioc_config
        for ioc_config in utils.find_iocs().values()
        if ioc_config.host == "localhost"
        or ioc_config.host == base_hostname
        or ioc_config.host == socket.gethostname()
    ]

    if len(iocs) == 0:
        print("No IOCs found on configured to run on this host.")
        print(f"Searched in: {utils.IOC_SEARCH_PATH}")
        return 1

    max_base_len = max(len(str(ioc.path)) for ioc in iocs) + EXTRA_PAD_WIDTH
    max_ioc_name_len = max(len(ioc.name) for ioc in iocs) + EXTRA_PAD_WIDTH
    max_user_len = max(len(ioc.user) for ioc in iocs) + EXTRA_PAD_WIDTH
    max_port_len = max(len(str(ioc.procserv_port)) for ioc in iocs) + EXTRA_PAD_WIDTH
    max_exec_len = max(len(ioc.exec_path) for ioc in iocs) + max_base_len - EXTRA_PAD_WIDTH

    header = (
        f"{'BASE'.ljust(max_base_len)}| {'IOC'.ljust(max_ioc_name_len)}| "
        f"{'USER'.ljust(max_user_len)}| {'PORT'.ljust(max_port_len)}| "
        f"{'EXEC'.ljust(max_exec_len)}"
    )
    print(header)
    print("-" * len(header))
    for ioc in iocs:
        ttime.sleep(0.01)
        print(
            f"{str(ioc.path).ljust(max_base_len)}| {ioc.name.ljust(max_ioc_name_len)}| "
            f"{ioc.user.ljust(max_user_len)}| {str(ioc.procserv_port).ljust(max_port_len)}| "
            f"{str(ioc.path / ioc.chdir / ioc.exec_path).ljust(max_exec_len)}"
        )


def disable(ioc: str):
    """Disable autostart for the given IOC."""

    _, _, ret = utils.systemctl_passthrough("disable", ioc)
    if ret == 0:
        print(f"Autostart disabled for IOC '{ioc}'")
    else:
        raise RuntimeError(f"Failed to disable autostart for IOC '{ioc}'!")
    return ret


def enable(ioc: str):
    """Enable autostart for the given IOC."""

    _, _, ret = utils.systemctl_passthrough("enable", ioc)
    if ret == 0:
        print(f"Autostart enabled for IOC '{ioc}'")
    else:
        raise RuntimeError(f"Failed to enable autostart for IOC '{ioc}'!")
    return ret


def start(ioc: str):
    """Start the given IOC."""

    _, _, ret = utils.systemctl_passthrough("start", ioc)
    if ret == 0:
        print(f"IOC '{ioc}' started successfully.")
    else:
        raise RuntimeError(f"Failed to start IOC '{ioc}'!")
    return ret


def startall():
    """Start all IOCs on this host."""

    iocs = utils.find_installed_iocs().values()
    ret = 0
    for ioc in iocs:
        ret += start(ioc.name)
    return ret


def stop(ioc: str):
    """Stop the given IOC."""

    _, _, ret = utils.systemctl_passthrough("stop", ioc)
    if ret == 0:
        print(f"IOC '{ioc}' stopped successfully.")
    else:
        raise RuntimeError(f"Failed to stop IOC '{ioc}'!")
    return ret


def stopall():
    """Stop all IOCs on this host."""

    iocs = utils.find_installed_iocs().values()
    ret = 0
    for ioc in iocs:
        ret += stop(ioc.name)
    return ret


def enableall():
    """Enable autostart for all IOCs on this host."""

    iocs = utils.find_installed_iocs().values()
    ret = 0
    for ioc in iocs:
        ret += enable(ioc.name)
    return ret


def disableall():
    """Disable autostart for all IOCs on this host."""

    iocs = utils.find_installed_iocs().values()
    ret = 0
    for ioc in iocs:
        ret += disable(ioc.name)
    return ret


def restart(ioc: str):
    """Restart the given IOC."""

    _, _, ret = utils.systemctl_passthrough("restart", ioc)
    if ret == 0:
        print(f"IOC '{ioc}' restarted successfully.")
    else:
        raise RuntimeError(f"Failed to restart IOC '{ioc}'!")
    return ret


def uninstall(ioc: str):
    """Uninstall the given IOC."""

    if not os.geteuid() == 0:
        raise PermissionError("You must be root to uninstall an IOC!")

    _, _, ret = utils.systemctl_passthrough("stop", ioc)
    if ret != 0:
        raise RuntimeError(f"Failed to stop IOC '{ioc}' before uninstalling!")
    _, _, ret = utils.systemctl_passthrough("disable", ioc)
    if ret != 0:
        raise RuntimeError(f"Failed to disable IOC '{ioc}' before uninstalling!")
    _, _, ret = utils.systemctl_passthrough("uninstall", ioc)
    if ret == 0:
        print(f"IOC '{ioc}' uninstalled successfully.")
    else:
        raise RuntimeError(f"Failed to uninstall IOC '{ioc}'!")
    return ret


def install(ioc: str):
    """Install the given IOC."""

    if not os.geteuid() == 0:
        raise PermissionError("You must be root to install an IOC!")

    service_file = utils.SYSTEMD_SERVICE_PATH / f"softioc-{ioc}.service"
    ioc_config = utils.find_iocs()[ioc]
    base_hostname = socket.gethostname()
    if "." in base_hostname:
        base_hostname = base_hostname.split(".")[0]

    if ioc_config.host not in [base_hostname, "localhost", socket.gethostname()]:
        raise RuntimeError(
            f"Cannot install IOC '{ioc}' on this host; configured host is '{ioc_config.host}'!"
        )

    if ioc_config.user == "root":
        raise RuntimeError(f"Refusing to install IOC '{ioc}' to run as user 'root'!")

    with open(service_file, "w") as f:
        f.write(
            f"""
#
# Installed by manage-iocs
#
[Unit]
Description=IOC {ioc} via procServ
After=network.target remote_fs.target local_fs.target syslog.target time.target centrifydc.service
ConditionFileIsExecutable=/usr/bin/procServ

[Service]
User={ioc_config.user}
ExecStart=/usr/bin/procServ -f -q -c {ioc_config.path} -i ^D^C^] -p /var/run/softioc-{ioc}.pid \
  -n {ioc} --restrict -L /var/log/softioc/{ioc}/{ioc}.log \
  {ioc_config.procserv_port} {ioc_config.path}/{ioc_config.exec_path}
Environment="PROCPORT={ioc_config.procserv_port}"
Environment="HOSTNAME={ioc_config.host}"
Environment="IOCNAME={ioc}"
Environment="TOP={ioc_config.path}"
#Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
        )

    _, stderr, ret = utils.systemctl_passthrough("install", ioc)
    if ret == 0:
        print(f"IOC '{ioc}' installed successfully.")
    else:
        raise RuntimeError(f"Failed to install IOC '{ioc}'!: {stderr.strip()}")
    return ret


def status():
    """Get the status of the given IOC."""

    ret = 0
    statuses: dict[str, tuple[str, bool]] = {}
    installed_iocs = utils.find_installed_iocs().keys()
    if len(installed_iocs) == 0:
        print("No Installed IOCs found on this host.")
        return 1

    for installed_ioc in installed_iocs:
        try:
            statuses[installed_ioc] = utils.get_ioc_status(installed_ioc)
        except RuntimeError:
            pass  # TODO: Handle this better?

    max_ioc_name_len = max(len(ioc_name) for ioc_name in statuses.keys()) + EXTRA_PAD_WIDTH
    max_status_len = max(len(status[0]) for status in statuses.values()) + EXTRA_PAD_WIDTH
    max_enabled_len = len("Auto-Start")

    print(f"{'IOC'.ljust(max_ioc_name_len)}{'Status'.ljust(max_status_len)}Auto-Start")
    ttime.sleep(0.01)
    print("-" * (max_ioc_name_len + max_status_len + max_enabled_len))
    for ioc_name, (state, is_enabled) in statuses.items():
        ttime.sleep(0.01)
        if state == "Running":
            state_str = f"\033[92m{state}\033[0m"  # Green
        elif state == "Stopped":
            state_str = f"\033[91m{state}\033[0m"  # Red
        else:
            state_str = f"\033[93m{state}\033[0m"  # Yellow
        print(
            f"{ioc_name.ljust(max_ioc_name_len)}{state_str.ljust(max_status_len + ANSI_COLOR_ESC_CODE_LEN)}{'Enabled' if is_enabled else 'Disabled'}"  # noqa: E501
        )

    return ret

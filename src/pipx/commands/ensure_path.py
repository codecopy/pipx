import logging
import site
import sys
import textwrap
from pathlib import Path
from typing import Optional, Tuple

import userpath  # type: ignore

from pipx import constants
from pipx.constants import EXIT_CODE_OK, ExitCode
from pipx.emojies import stars

logger = logging.getLogger(__name__)


def get_pipx_user_bin_path() -> Optional[Path]:
    """Returns None if pipx is not installed using `pip --user`
    Otherwise returns parent dir of pipx binary
    """
    # NOTE: using this method to detect pip user-installed pipx will return
    #   None if pipx was installed as editable using `pip install --user -e`

    # https://docs.python.org/3/install/index.html#inst-alt-install-user
    #   Linux + Mac:
    #       scripts in <userbase>/bin
    #   Windows:
    #       scripts in <userbase>/Python<XY>/Scripts
    #       modules in <userbase>/Python<XY>/site-packages

    pipx_bin_path = None

    script_path = Path(__file__).resolve()
    userbase_path = Path(site.getuserbase()).resolve()
    try:
        _ = script_path.relative_to(userbase_path)
    except ValueError:
        pip_user_installed = False
    else:
        pip_user_installed = True
    if pip_user_installed:
        test_paths = (
            userbase_path / "bin" / "pipx",
            Path(site.getusersitepackages()).resolve().parent / "Scripts" / "pipx.exe",
        )
        for test_path in test_paths:
            if test_path.exists():
                pipx_bin_path = test_path.parent
                break

    return pipx_bin_path


def ensure_path(location: Path, *, force: bool) -> Tuple[bool, bool]:
    """Ensure location is in user's PATH or add it to PATH.
    Returns True if location was added to PATH
    """
    location_str = str(location)
    path_added = False
    need_shell_restart = userpath.need_shell_restart(location_str)
    in_current_path = userpath.in_current_path(location_str)

    if force or (not in_current_path and not need_shell_restart):
        userpath.append(location_str)
        print(
            textwrap.fill(
                f"Success! Added {location_str} to the PATH environment variable.",
                subsequent_indent="    ",
            )
        )
        path_added = True
        need_shell_restart = userpath.need_shell_restart(location_str)
    elif not in_current_path and need_shell_restart:
        print(
            textwrap.fill(
                f"{location_str} has been been added to PATH, but you "
                "need to open a new terminal or re-login for this PATH "
                "change to take effect.",
                subsequent_indent="    ",
            )
        )
    else:
        print(
            textwrap.fill(
                f"{location_str} is already in PATH.", subsequent_indent="    "
            )
        )

    return (path_added, need_shell_restart)


def ensure_pipx_paths(force: bool) -> ExitCode:
    """Returns pipx exit code."""
    bin_paths = [constants.LOCAL_BIN_DIR]

    pipx_user_bin_path = get_pipx_user_bin_path()
    if pipx_user_bin_path is not None:
        bin_paths.append(pipx_user_bin_path)

    path_added = False
    need_shell_restart = False
    for bin_path in bin_paths:
        (path_added_current, need_shell_restart_current) = ensure_path(
            bin_path, force=force
        )
        path_added |= path_added_current
        need_shell_restart |= need_shell_restart_current

    print()

    if path_added:
        print(
            textwrap.fill(
                "Consider adding shell completions for pipx. "
                "Run 'pipx completions' for instructions."
            )
            + "\n"
        )
    elif not need_shell_restart:
        sys.stdout.flush()
        logger.warning(
            textwrap.fill(
                "All pipx binary directories have been added to PATH. "
                "If you are sure you want to proceed, try again with "
                "the '--force' flag."
            )
            + "\n"
        )

    if need_shell_restart:
        print(
            textwrap.fill(
                "You will need to open a new terminal or re-login for "
                "the PATH changes to take effect."
            )
            + "\n"
        )

    print(f"Otherwise pipx is ready to go! {stars}")

    return EXIT_CODE_OK

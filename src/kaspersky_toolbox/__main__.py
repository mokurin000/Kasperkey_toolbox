"""Entry point for `python -m kaspersky_toolbox`."""

from kaspersky_toolbox.app import KasperskyToolboxApp
from kaspersky_toolbox.singleton import SingletonGuard
from kaspersky_toolbox.utils import is_admin, run_as_admin


def main() -> None:
    # Admin elevation — re-launch if not elevated
    if not is_admin():
        run_as_admin()

    # Singleton guard — exit if another instance is running
    with SingletonGuard():  # noqa: F821
        app = KasperskyToolboxApp()
        app.run()


if __name__ == "__main__":
    main()

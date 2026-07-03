"""Entry point for `python -m kaspersky_toolbox`."""

from kaspersky_toolbox.app import KasperskyToolboxApp


def main() -> None:
    app = KasperskyToolboxApp()
    app.run()


if __name__ == "__main__":
    main()

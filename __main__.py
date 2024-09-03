#!/usr/bin/env python
# from PySide6 import QtCore
import ui
import sys
import logging
import argparse

from PySide6 import QtWidgets


def main():
    logging.basicConfig(
        format='[%(levelname)s] %(message)s',
        level='INFO'
    )

    parser = argparse.ArgumentParser(description="Simple ISMRMRD data cleaner.")
    parser.add_argument('file', type=str, nargs='?', help="ISMRMRD data file.")
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("MRD Cleaner")

    main = ui.MainWindow()
    main.resize(800, 600)
    main.show()

    if args.file:
        main.open_file(args.file)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
=========================================================================================
📌 파일명:      main.py
📌 설명:        AVAS40 WAV to Binary Converter 메인 실행 파일
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
=========================================================================================
"""

import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 
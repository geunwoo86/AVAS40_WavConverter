#!/usr/bin/env python3
"""
=========================================================================================
📌 파일명:      AVAS40_Sound Convertor.py
📌 설명:        AVAS40 WAV to Binary Converter - 모듈화된 메인 진입점
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15 (모듈화 업데이트)
📌 버전:        1.00
=========================================================================================
📌 변경 이력
-----------------------------------------------------------------------------------------
날짜          | 작성자        | 버전   | 변경 내용
-----------------------------------------------------------------------------------------
2025-05-29   | Geunwoo Lee   | 1.00  | 최초 작성
2025-01-15   | Geunwoo Lee   | 1.00  | 모듈화 구조로 리팩터링

=========================================================================================
📌 사용 방법:
    - 배포 메뉴얼 참조
    - python AVAS40_Sound Convertor.py 또는 python main.py로 실행 가능
=========================================================================================
📌 의존성:
    - Python ver 3.12.3
    - 필수 추가 파일 : flac.exe, libFLAC.dll
    - PyQt5
=========================================================================================
📌 모듈 구조:
    - utils.py: 상수와 유틸리티 함수
    - config.py: 설정 관리
    - processing.py: 프로세싱 스레드와 주소 설정 다이얼로그
    - dialogs.py: 설정 다이얼로그
    - main_window.py: 메인 윈도우 클래스
    - main.py: 메인 실행 파일
=========================================================================================
"""

# 기존 파일명 호환성을 위해 main.py의 내용을 그대로 포함
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

# 기존 코드와의 호환성을 위한 import (필요시 사용 가능)
from utils import *
from config import *
from processing import *
from dialogs import *
from main_window import *
"""
=========================================================================================
📌 파일명:      utils.py
📌 설명:        AVAS40 WavConverter 유틸리티 함수와 상수 모음
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
=========================================================================================
"""

import os
import sys

# 상수 정의
LOG_WIDTH = 100
TOOL_VERSION = "1.00"

def get_exe_directory():
    """exe 파일이 있는 디렉토리를 반환"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 실행된 경우
        return os.path.dirname(sys.executable)
    else:
        # 스크립트로 실행된 경우
        return os.path.dirname(os.path.abspath(__file__)) 
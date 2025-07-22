"""
=========================================================================================
📌 파일명:      utils.py
📌 설명:        AVAS40 Sound Convertor 유틸리티 함수와 상수 모음
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
=========================================================================================
"""

import os
import sys

# 기본 상수 정의
LOG_WIDTH = 100
TOOL_VERSION = "1.00"

class AudioConstants:
    """오디오 처리 관련 상수들"""
    # Magic Key
    MAGIC_KEY = 0x5AA55AA5
    
    # 헤더 크기
    ENGINE_HEADER_SIZE = 44  # Magic key(4) + Sound positions(40)
    EVENT_HEADER_SIZE = 8    # Event header (8 bytes)
    
    # 파일명 버퍼 크기
    FILENAME_BUFFER_SIZE = 80
    
    # 메모리 정렬
    WORD_ALIGNMENT = 4
    
    # HEX 데이터 오프셋
    FLAC_SIZE_OFFSET = 0x0000
    ENGINE_FILENAME_OFFSET = 0x0004
    ENGINE_FLAC_DATA_OFFSET = 0x0054
    EVENT_FLAC_DATA_OFFSET = 0x0004
    
    # 기본 압축 설정
    DEFAULT_COMPRESSION = "8"
    DEFAULT_BLOCK_SIZE = "512"
    
    # 기본 주소
    DEFAULT_START_ADDRESS = "10118000"

class FileConstants:
    """파일 처리 관련 상수들"""
    # 폴더명
    OUTPUT_FOLDER = "Output"
    ENGINE_FOLDER = "EngineSound"
    EVENT_FOLDER = "EventSound"
    
    # 파일명
    ENGINE_BIN_FILE = "MergedEngineSound.bin"
    ENGINE_HEADER_FILE = "EngineSound_VARIANT.h"
    EVENT_HEX_FILE = "MergedEventSound.hex"

class UIConstants:
    """UI 관련 상수들"""
    # 윈도우 크기
    MAIN_WINDOW_WIDTH = 800
    MAIN_WINDOW_HEIGHT = 600
    SETTINGS_DIALOG_WIDTH = 440
    SETTINGS_DIALOG_HEIGHT = 180
    
    # 테이블 컬럼 크기
    WAV_FILE_COLUMN_WIDTH = 600
    ADDRESS_COLUMN_WIDTH = 200
    TABLE_MARGIN = 25

# 예외 클래스들
class ProcessingError(Exception):
    """일반적인 처리 오류"""
    pass

class AudioFileError(ProcessingError):
    """오디오 파일 관련 오류"""
    pass

class FlacConversionError(AudioFileError):
    """FLAC 변환 오류"""
    pass

class HexDataError(ProcessingError):
    """HEX 데이터 처리 오류"""
    pass

class FilePermissionError(ProcessingError):
    """파일 권한 오류"""
    pass

def get_exe_directory():
    """exe 파일이 있는 디렉토리를 반환"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 실행된 경우
        return os.path.dirname(sys.executable)
    else:
        # 스크립트로 실행된 경우
        return os.path.dirname(os.path.abspath(__file__)) 
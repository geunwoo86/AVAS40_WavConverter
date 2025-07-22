#!/usr/bin/env python3
"""
=========================================================================================
📌 File:         AVAS40_Sound_Converter.py
📌 Description:  Compatibility entry point for AVAS40 WAV to Binary Converter
📌 Author:       Geunwoo Lee
📌 Date:         2025-01-15 (modularization update)
📌 Version:      1.00
=========================================================================================
📌 Main Features:
    - Maintains compatibility with legacy filename (AVAS40_WavConverter.py → AVAS40_Sound_Converter.py)
    - Provides same functionality as main.py
    - Imports all modules for full feature access
    - Compatibility interface for legacy users
    
📌 Change Log:
    - 2025-05-29: Initial creation (monolithic structure)
    - 2025-01-15: Refactored to modular structure
    
📌 How to Run:
    - Direct: python AVAS40_Sound_Converter.py
    - Recommended: python main.py
    - All legacy features available
    
📌 Dependencies:
    - Python ver 3.12.3
    - PyQt5
    - Required external files: flac.exe, libFLAC.dll
    - All local modules (utils, config, processing, dialogs, main_window, main)
    
📌 Module Structure:
    - utils.py: Constants, utility functions, exception classes
    - config.py: JSON-based settings management
    - audio_processor.py: WAV/FLAC conversion and HEX data generation
    - file_manager.py: File/log saving and path management
    - processing.py: Background processing thread and address dialog
    - dialogs.py: Output path settings dialog
    - main_window.py: Main UI window
    - main.py: Actual entry point (recommended)
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
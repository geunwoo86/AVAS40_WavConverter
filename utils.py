"""
=========================================================================================
📌 File:         utils.py
📌 Description:  Utility functions, constants, and exception classes for AVAS40 WavConverter
📌 Author:       Geunwoo Lee
📌 Date:         2025-01-15
📌 Version:      1.00
=========================================================================================
📌 Main Features:
    - AudioConstants: Audio processing constants (Magic Key, header size, offsets, etc.)
    - FileConstants: File and folder name constants
    - UIConstants: UI size and layout constants
    - Exception classes: ProcessingError, AudioFileError, FlacConversionError, etc.
    - get_exe_directory(): Utility function to get the executable directory
    
📌 Key Constants:
    - MAGIC_KEY: Engine sound Magic Key (0x5AA55AA5)
    - ENGINE_HEADER_SIZE: Engine header size (44 bytes)
    - EVENT_HEADER_SIZE: Event header size (8 bytes)
    - DEFAULT_COMPRESSION: Default compression level ("8")
    - DEFAULT_START_ADDRESS: Default start address ("10118000")
    
📌 Dependencies:
    - Standard library: os, sys
=========================================================================================
"""

import os
import sys

# Basic constants
LOG_WIDTH = 100
TOOL_VERSION = "1.00"

class AudioConstants:
    """Audio processing related constants"""
    # Magic Key
    MAGIC_KEY = 0x5AA55AA5
    
    # Header size
    ENGINE_HEADER_SIZE = 44  # Magic key(4) + Sound positions(40)
    EVENT_HEADER_SIZE = 8    # Event header (8 bytes)
    
    # Filename buffer size
    FILENAME_BUFFER_SIZE = 80
    
    # Memory alignment
    WORD_ALIGNMENT = 4
    
    # HEX data offsets
    FLAC_SIZE_OFFSET = 0x0000
    ENGINE_FILENAME_OFFSET = 0x0004
    ENGINE_FLAC_DATA_OFFSET = 0x0054
    EVENT_FLAC_DATA_OFFSET = 0x0004
    
    # Default compression settings
    DEFAULT_COMPRESSION = "8"
    DEFAULT_BLOCK_SIZE = "512"
    
    # Default address
    DEFAULT_START_ADDRESS = "10118000"

class FileConstants:
    """File processing related constants"""
    # Folder names
    OUTPUT_FOLDER = "Output"
    ENGINE_FOLDER = "EngineSound"
    EVENT_FOLDER = "EventSound"
    
    # File names
    ENGINE_BIN_FILE = "MergedEngineSound.bin"
    ENGINE_HEADER_FILE = "EngineSound_VARIANT.h"
    EVENT_HEX_FILE = "MergedEventSound.hex"

class UIConstants:
    """UI related constants"""
    # Window size
    MAIN_WINDOW_WIDTH = 800
    MAIN_WINDOW_HEIGHT = 600
    SETTINGS_DIALOG_WIDTH = 440
    SETTINGS_DIALOG_HEIGHT = 180
    
    # Table column size
    WAV_FILE_COLUMN_WIDTH = 600
    ADDRESS_COLUMN_WIDTH = 200
    TABLE_MARGIN = 25

# Exception classes
class ProcessingError(Exception):
    """General processing error"""
    pass

class AudioFileError(ProcessingError):
    """Audio file related error"""
    pass

class FlacConversionError(AudioFileError):
    """FLAC conversion error"""
    pass

class HexDataError(ProcessingError):
    """HEX data processing error"""
    pass

class FilePermissionError(ProcessingError):
    """File permission error"""
    pass

def get_exe_directory():
    """Return the directory where the exe/script is located"""
    if getattr(sys, 'frozen', False):
        # If running with PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # If running as a script
        return os.path.dirname(os.path.abspath(__file__)) 
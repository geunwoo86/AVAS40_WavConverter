"""
=========================================================================================
📌 File:         config.py
📌 Description:  Settings management module for AVAS40 WavGenerator
📌 Author:       Geunwoo Lee
📌 Date:         2025-01-15
📌 Version:      1.00
=========================================================================================
📌 Main Features:
    - Settings class: Application settings management
    - JSON-based settings file read/write (settings.json)
    - Output path management (default vs. custom)
    - app_settings: Global settings instance
    
📌 Settings Fields:
    - use_default_path: Whether to use default output path (True/False)
    - custom_output_path: User-defined output path
    - settings_file: Path to settings file (located in executable directory)
    
📌 Key Methods:
    - load_settings(): Load settings from file
    - save_settings(): Save settings to file
    - get_output_base_path(): Get current base output path
    
📌 Dependencies:
    - Standard library: os, json
    - Local module: utils.get_exe_directory
=========================================================================================
"""

import os
import json
from utils import get_exe_directory

class Settings:
    def __init__(self):
        self.use_default_path = True
        self.custom_output_path = ""
        self.settings_file = os.path.join(get_exe_directory(), "settings.json")
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.use_default_path = data.get('use_default_path', True)
                    self.custom_output_path = data.get('custom_output_path', "")
        except Exception as e:
            # If loading fails, use default values
            self.use_default_path = True
            self.custom_output_path = ""
    
    def save_settings(self):
        """Save settings to file"""
        try:
            data = {
                'use_default_path': self.use_default_path,
                'custom_output_path': self.custom_output_path
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Settings save failed: {e}")
    
    def get_output_base_path(self):
        """Return the base output path"""
        if self.use_default_path or not self.custom_output_path:
            return get_exe_directory()
        else:
            return self.custom_output_path

# 전역 설정 인스턴스
app_settings = Settings() 
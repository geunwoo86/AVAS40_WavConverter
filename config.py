"""
=========================================================================================
📌 파일명:      config.py
📌 설명:        AVAS40 WavConverter 설정 관리 모듈
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
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
        """설정 파일에서 설정 로드"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.use_default_path = data.get('use_default_path', True)
                    self.custom_output_path = data.get('custom_output_path', "")
        except Exception as e:
            # 설정 파일 로드 실패시 기본값 사용
            self.use_default_path = True
            self.custom_output_path = ""
    
    def save_settings(self):
        """설정을 파일에 저장"""
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
        """출력 기본 경로 반환"""
        if self.use_default_path or not self.custom_output_path:
            return get_exe_directory()
        else:
            return self.custom_output_path

# 전역 설정 인스턴스
app_settings = Settings() 
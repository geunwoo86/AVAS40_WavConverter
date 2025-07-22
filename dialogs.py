"""
=========================================================================================
📌 파일명:      dialogs.py
📌 설명:        AVAS40 WavConverter 다이얼로그 클래스들 (리팩토링됨)
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
=========================================================================================
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox)
from config import app_settings
from utils import get_exe_directory, UIConstants
from file_manager import OutputPathManager

class SettingsDialog(QDialog):
    """설정 다이얼로그 클래스 (리팩토링됨)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setup_ui()
        self.setFixedSize(UIConstants.SETTINGS_DIALOG_WIDTH, UIConstants.SETTINGS_DIALOG_HEIGHT)
        
    def setup_ui(self):
        """설정 다이얼로그 UI 구성"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Current Output Path 그룹
        layout.addWidget(self._create_current_path_group())
        
        # Change Output Path 그룹
        layout.addWidget(self._create_change_path_group())
        
        # Apply/Cancel 버튼
        layout.addLayout(self._create_button_layout())
        
        # 초기 표시 업데이트
        self.update_current_path_display()
        
    def _create_current_path_group(self) -> QGroupBox:
        """현재 경로 표시 그룹 생성"""
        current_group = QGroupBox("Current Output Path")
        current_layout = QVBoxLayout()
        current_layout.setContentsMargins(8, 5, 8, 5)
        
        self.current_path_display = QLabel()
        self.current_path_display.setWordWrap(True)
        current_layout.addWidget(self.current_path_display)
        current_group.setLayout(current_layout)
        return current_group
        
    def _create_change_path_group(self) -> QGroupBox:
        """경로 변경 그룹 생성"""
        change_group = QGroupBox("Change Output Path")
        change_layout = QVBoxLayout()
        change_layout.setContentsMargins(8, 5, 8, 5)
        change_layout.setSpacing(5)
        
        # Output Path 입력 필드와 Browse 버튼
        path_layout = QHBoxLayout()
        path_layout.setSpacing(5)
        path_layout.addWidget(QLabel("Output Path:"))
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        # 현재 설정된 경로를 표시
        current_path = app_settings.get_output_base_path()
        self.output_path_edit.setText(current_path)
        path_layout.addWidget(self.output_path_edit)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output_path)
        path_layout.addWidget(self.browse_btn)
        
        change_layout.addLayout(path_layout)
        
        # Reset to Default 버튼
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self.reset_to_default)
        change_layout.addWidget(self.reset_btn)
        
        change_group.setLayout(change_layout)
        return change_group
    
    def _create_button_layout(self) -> QHBoxLayout:
        """버튼 레이아웃 생성"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setMinimumWidth(80)
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        return button_layout
        
    def browse_output_path(self):
        """출력 경로 선택"""
        current_path = self.output_path_edit.text()
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Folder", 
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder:
            self.output_path_edit.setText(folder)
            self.update_current_path_display()
    
    def update_current_path_display(self):
        """현재 출력 경로 표시 업데이트"""
        current_path = self.output_path_edit.text().strip()
        if not current_path:
            current_path = get_exe_directory()
        
        # (Default) 표시 여부 결정
        default_path = get_exe_directory()
        if current_path == default_path:
            display_text = f"{current_path} (Default)"
        else:
            display_text = current_path
            
        self.current_path_display.setText(display_text)
    
    def reset_to_default(self):
        """기본 경로로 재설정"""
        default_path = get_exe_directory()
        self.output_path_edit.setText(default_path)
        self.update_current_path_display()
    
    def apply_settings(self):
        """설정 적용"""
        new_path = self.output_path_edit.text().strip()
        
        if not self._validate_path(new_path):
            return
        
        # 설정 저장
        self._save_path_settings(new_path)
        
        QMessageBox.information(self, "Information", "Output path has been successfully changed.")
        self.accept()
    
    def _validate_path(self, path: str) -> bool:
        """경로 유효성 검사"""
        if not path:
            QMessageBox.warning(self, "Warning", "Please enter a path.")
            return False
        
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Warning", "The specified path does not exist.")
            return False
        
        if not os.access(path, os.W_OK):
            QMessageBox.warning(self, "Warning", 
                              f"No write permission for directory: {path}")
            return False
        
        return True
    
    def _save_path_settings(self, new_path: str):
        """경로 설정 저장"""
        default_path = get_exe_directory()
        
        if new_path == default_path:
            app_settings.use_default_path = True
            app_settings.custom_output_path = ""
        else:
            app_settings.use_default_path = False
            app_settings.custom_output_path = new_path
            
        app_settings.save_settings() 
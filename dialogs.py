"""
=========================================================================================
📌 File:         dialogs.py
📌 Description:  Dialog classes for AVAS40 WavGenerator (refactored)
📌 Author:       Geunwoo Lee
📌 Date:         2025-01-15
📌 Version:      1.00
=========================================================================================
📌 Main Features:
    - SettingsDialog: Output path settings dialog
    - Display current output path (default vs. custom)
    - Change output path and validate
    - Save and load settings
    
📌 SettingsDialog Key Methods:
    - setup_ui(): UI setup (current path, change options, buttons)
    - browse_output_path(): Folder selection dialog
    - reset_to_default(): Reset to default path
    - apply_settings(): Apply and save settings
    - update_current_path_display(): Update current path display
    
📌 UI Structure:
    - Current Output Path: Shows current output path
    - Change Output Path: Interface for changing path
    - Browse button: Folder selection dialog
    - Reset to Default: Restore default path
    - Apply/Cancel buttons: Apply/cancel settings
    
📌 Validation Features:
    - Check if path exists
    - Check write permission
    - Prevent empty path input
    
📌 Dependencies:
    - Standard library: os
    - PyQt5: QDialog, QGroupBox, QFileDialog, etc.
    - Local modules: config, utils
=========================================================================================
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox)
from config import app_settings
from utils import get_exe_directory, UIConstants
from file_manager import OutputPathManager

class SettingsDialog(QDialog):
    """Settings dialog class (refactored)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setup_ui()
        self.setFixedSize(UIConstants.SETTINGS_DIALOG_WIDTH, UIConstants.SETTINGS_DIALOG_HEIGHT)
        
    def setup_ui(self):
        """UI setup for settings dialog"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Current Output Path group
        layout.addWidget(self._create_current_path_group())
        
        # Change Output Path group
        layout.addWidget(self._create_change_path_group())
        
        # Apply/Cancel buttons
        layout.addLayout(self._create_button_layout())
        
        # Initial display update
        self.update_current_path_display()
        
    def _create_current_path_group(self) -> QGroupBox:
        """Create group for displaying current path"""
        current_group = QGroupBox("Current Output Path")
        current_layout = QVBoxLayout()
        current_layout.setContentsMargins(8, 5, 8, 5)
        
        self.current_path_display = QLabel()
        self.current_path_display.setWordWrap(True)
        current_layout.addWidget(self.current_path_display)
        current_group.setLayout(current_layout)
        return current_group
        
    def _create_change_path_group(self) -> QGroupBox:
        """Create group for changing output path"""
        change_group = QGroupBox("Change Output Path")
        change_layout = QVBoxLayout()
        change_layout.setContentsMargins(8, 5, 8, 5)
        change_layout.setSpacing(5)
        
        # Output Path input field and Browse button
        path_layout = QHBoxLayout()
        path_layout.setSpacing(5)
        path_layout.addWidget(QLabel("Output Path:"))
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        # Display current set path
        current_path = app_settings.get_output_base_path()
        self.output_path_edit.setText(current_path)
        path_layout.addWidget(self.output_path_edit)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self.browse_output_path)
        path_layout.addWidget(self.browse_btn)
        
        change_layout.addLayout(path_layout)
        
        # Reset to Default button
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self.reset_to_default)
        change_layout.addWidget(self.reset_btn)
        
        change_group.setLayout(change_layout)
        return change_group
    
    def _create_button_layout(self) -> QHBoxLayout:
        """Create button layout"""
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
        """Select output path"""
        current_path = self.output_path_edit.text()
        
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Select Output Folder")
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.DontResolveSymlinks, True)
        
        # Set button texts to English
        dialog.setLabelText(QFileDialog.FileName, "Folder:")
        dialog.setLabelText(QFileDialog.Accept, "Select Folder")
        dialog.setLabelText(QFileDialog.Reject, "Cancel")
        
        if current_path:
            dialog.setDirectory(current_path)
        
        if dialog.exec_() == QFileDialog.Accepted:
            folder = dialog.selectedFiles()[0]
            self.output_path_edit.setText(folder)
            self.update_current_path_display()
    
    def update_current_path_display(self):
        """Update display of current output path"""
        current_path = self.output_path_edit.text().strip()
        if not current_path:
            current_path = get_exe_directory()
        
        # Decide whether to display (Default)
        default_path = get_exe_directory()
        if current_path == default_path:
            display_text = f"{current_path} (Default)"
        else:
            display_text = current_path
            
        self.current_path_display.setText(display_text)
    
    def reset_to_default(self):
        """Reset to default path"""
        default_path = get_exe_directory()
        self.output_path_edit.setText(default_path)
        self.update_current_path_display()
    
    def apply_settings(self):
        """Apply settings"""
        new_path = self.output_path_edit.text().strip()
        
        if not self._validate_path(new_path):
            return
        
        # Save settings
        self._save_path_settings(new_path)
        
        QMessageBox.information(self, "Information", "Output path has been successfully changed.")
        self.accept()
    
    def _validate_path(self, path: str) -> bool:
        """Validate path"""
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
        """Save path settings"""
        default_path = get_exe_directory()
        
        if new_path == default_path:
            app_settings.use_default_path = True
            app_settings.custom_output_path = ""
        else:
            app_settings.use_default_path = False
            app_settings.custom_output_path = new_path
            
        app_settings.save_settings() 
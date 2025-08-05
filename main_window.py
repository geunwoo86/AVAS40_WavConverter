"""
=========================================================================================
📌 File:         main_window.py
📌 Description:  Main window class for AVAS40 WavGenerator (refactored)
📌 Author:       Geunwoo Lee
📌 Date:         2025-01-15
📌 Version:      1.00
=========================================================================================
📌 Main Features:
    - MainWindow: Main UI window of the application
    - Input folder selection, conversion settings, sound type selection GUI
    - Real-time log display and log saving
    - Drag & drop support, menu bar (settings)
    - Linked with ProcessingThread for background processing
    
📌 MainWindow Key Methods:
    - _setup_ui(): UI setup (input, settings, type, address, buttons, log)
    - start_processing(): Start processing and run thread
    - update_fields(): Update fields by sound type
    - show_sound_info_dialog(): Show engine address dialog
    - save_log(): Save log as CSV file
    - append_log(): Add real-time log message
    
📌 UI Structure:
    - Input Settings: Input folder selection (drag & drop supported)
    - Conversion Settings: Compression level, block size (disabled)
    - Sound Type: Engine/Event radio buttons
    - Address Settings: Start address (auto change by type)
    - Action buttons: Start Processing, Save Log
    - Log area: Real-time processing status
    
📌 Features:
    - Engine type: Address "10118000" + disabled
    - Event type: Address "00001000" + enabled
    - Drag & drop folder selection
    - Background processing prevents UI block
    
📌 Dependencies:
    - Standard library: os, csv, datetime
    - PyQt5: QMainWindow, QWidget, QVBoxLayout, etc.
    - Local modules: config, utils, processing, dialogs, file_manager
=========================================================================================
"""

import os
import csv
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QRadioButton,
                            QTextEdit, QFileDialog, QMessageBox, QAction, QDialog)
from config import app_settings
from utils import TOOL_VERSION, LOG_WIDTH, AudioConstants, UIConstants
from processing import ProcessingThread, AddressSettingDialog
from dialogs import SettingsDialog
from file_manager import LogManager, OutputPathManager

class MainWindow(QMainWindow):
    """Main window class (refactored)"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"AVAS40 Sound Generator v{TOOL_VERSION}")
        self.setGeometry(100, 100, UIConstants.MAIN_WINDOW_WIDTH, UIConstants.MAIN_WINDOW_HEIGHT)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Set up menu bar
        self.setup_menu_bar()
        
        # Set up UI
        self._setup_ui()
        
        # Initialize processing objects
        self._init_processing_objects()
        
        # Set initial state
        self.update_fields()
        
    def _setup_ui(self):
        """Set up UI"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Input folder selection group
        layout.addWidget(self._create_input_group())
        
        # Settings group
        layout.addWidget(self._create_settings_group())
        
        # Sound type group
        layout.addWidget(self._create_sound_type_group())
        
        # Address settings group
        layout.addWidget(self._create_address_group())
        
        # Button group
        layout.addLayout(self._create_button_layout())
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
    
    def _create_input_group(self) -> QGroupBox:
        """Create input folder selection group"""
        input_group = QGroupBox("Folder Selection")
        input_layout = QGridLayout()
        
        self.input_folder_edit = QLineEdit()
        self.input_folder_edit.setAcceptDrops(True)
        self.input_folder_edit.dragEnterEvent = self.dragEnterEvent
        self.input_folder_edit.dropEvent = self.dropEvent
        
        self.browse_button = QPushButton("Open Folder")
        self.browse_button.clicked.connect(self.browse_folder)
        
        input_layout.addWidget(QLabel("Input Folder:"), 0, 0)
        input_layout.addWidget(self.input_folder_edit, 0, 1)
        input_layout.addWidget(self.browse_button, 0, 2)
        
        input_group.setLayout(input_layout)
        return input_group
    
    def _create_settings_group(self) -> QGroupBox:
        """Create settings group"""
        settings_group = QGroupBox("FLAC Encoding Settings")
        settings_layout = QGridLayout()
        
        # Compression level
        self.compression_combo = QComboBox()
        self.compression_combo.addItems([str(x) for x in range(11)])
        self.compression_combo.setCurrentText(AudioConstants.DEFAULT_COMPRESSION)
        self.compression_combo.setEnabled(False)  # Disabled
        
        # Block size
        self.block_size_combo = QComboBox()
        self.block_size_combo.addItems(["128", "256", "512", "1024", "2048", "4096"])
        self.block_size_combo.setCurrentText(AudioConstants.DEFAULT_BLOCK_SIZE)
        self.block_size_combo.setEnabled(False)  # Disabled
        
        settings_layout.addWidget(QLabel("Compression:"), 0, 0)
        settings_layout.addWidget(self.compression_combo, 0, 1)
        settings_layout.addWidget(QLabel("Block Size:"), 0, 2)
        settings_layout.addWidget(self.block_size_combo, 0, 3)
        
        settings_group.setLayout(settings_layout)
        return settings_group
    
    def _create_sound_type_group(self) -> QGroupBox:
        """Create sound type group"""
        sound_group = QGroupBox("Sound Type")
        sound_layout = QHBoxLayout()
        
        self.engine_radio = QRadioButton("Engine")
        self.event_radio = QRadioButton("Event")
        self.engine_radio.setChecked(True)
        self.engine_radio.toggled.connect(self.update_fields)
        
        sound_layout.addWidget(self.engine_radio)
        sound_layout.addWidget(self.event_radio)
        sound_group.setLayout(sound_layout)
        return sound_group
    
    def _create_address_group(self) -> QGroupBox:
        """Create address settings group"""
        address_group = QGroupBox("Address Settings")
        address_layout = QGridLayout()
        
        self.start_address_edit = QLineEdit(AudioConstants.DEFAULT_START_ADDRESS)
        
        address_layout.addWidget(QLabel("Start Address (Hex):"), 0, 0)
        address_layout.addWidget(self.start_address_edit, 0, 1)
        
        address_group.setLayout(address_layout)
        return address_group
    
    def _create_button_layout(self) -> QHBoxLayout:
        """Create button layout"""
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Generate Files")
        self.start_button.clicked.connect(self.start_processing)
        self.save_button = QPushButton("Save Log")
        self.save_button.clicked.connect(self.save_log)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.save_button)
        return button_layout
    
    def _init_processing_objects(self):
        """Initialize processing objects"""
        # Processing thread
        self.processing_thread = ProcessingThread()
        self.processing_thread.log_message.connect(self.append_log)
        self.processing_thread.finished.connect(self.enable_buttons)
        self.processing_thread.save_log.connect(lambda: self.save_log(auto_save=True))
        self.processing_thread.show_info_dialog.connect(self.show_sound_info_dialog)
        self.processing_thread.no_wav_files.connect(self.handle_no_wav_files)
        
        # Log manager is initialized at processing start
        self.log_manager = None
        
    def dragEnterEvent(self, event):
        """Handle drag and drop event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle drop event"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.input_folder_edit.setText(path)
            else:
                QMessageBox.warning(self, "Warning", "Please drop a folder, not a file.")
        
    def browse_folder(self):
        """Open folder selection dialog"""
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Select Folder with WAV Files")
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.DontResolveSymlinks, True)
        
        # Set button texts to English
        dialog.setLabelText(QFileDialog.FileName, "Folder:")
        dialog.setLabelText(QFileDialog.Accept, "Select Folder")
        dialog.setLabelText(QFileDialog.Reject, "Cancel")
        
        if dialog.exec_() == QFileDialog.Accepted:
            folder = dialog.selectedFiles()[0]
            self.input_folder_edit.setText(folder)
    
    def setup_menu_bar(self):
        """Set up menu bar"""
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('Settings')
        output_path_action = QAction('Output Path Settings', self)
        output_path_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(output_path_action)

    def open_settings_dialog(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec_()
        
    def update_fields(self):
        """Update fields by sound type"""
        is_engine = self.engine_radio.isChecked()
        
        if is_engine:
            # Engine type: Address "10118000" + disabled
            self.start_address_edit.setText("10118000")
            self.start_address_edit.setEnabled(False)
        else:
            # Event type: Address "00001000" + enabled
            self.start_address_edit.setText("00001000")
            self.start_address_edit.setEnabled(True)
        
    def start_processing(self):
        """Start processing"""
        if not self._validate_input():
            return
        
        # Initialize log manager
        sound_type = "Engine Sound" if self.engine_radio.isChecked() else "Event Sound"
        self.log_manager = LogManager(sound_type)
        
        # Disable UI
        self.disable_buttons()
        
        # Clear log
        self.log_text.clear()
        
        # Set processing parameters
        self._set_processing_parameters()
        
        # Start processing
        self.processing_thread.start()
        
    def _validate_input(self) -> bool:
        """Validate input"""
        input_folder = self.input_folder_edit.text()
        if not input_folder:
            QMessageBox.warning(self, "Warning", "Please select an input folder.")
            return False
            
        if not os.path.exists(input_folder):
            QMessageBox.warning(self, "Warning", "Selected folder does not exist.")
            return False
            
        # Validate address (only for Event Sound)
        if self.event_radio.isChecked():
            try:
                int(self.start_address_edit.text(), 16)
            except ValueError:
                QMessageBox.warning(self, "Warning", "Please enter a valid hexadecimal address.")
                return False
        
        return True
    
    def _set_processing_parameters(self):
        """Set processing parameters"""
        input_folder = self.input_folder_edit.text()
        compression_level = self.compression_combo.currentText()
        block_size = self.block_size_combo.currentText()
        sound_type = "Engine Sound" if self.engine_radio.isChecked() else "Event Sound"
        hex_start_address = self.start_address_edit.text()
        hex_file_size_kb = "864.00"  # Default value
        
        self.processing_thread.set_parameters(
            input_folder, compression_level, block_size, 
            sound_type, hex_start_address, hex_file_size_kb
        )
        
    def disable_buttons(self):
        """Disable buttons"""
        self.start_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
    def enable_buttons(self):
        """Enable buttons"""
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
    def append_log(self, message):
        """Add log message"""
        self.log_text.append(message)
        # Also add to log manager
        if self.log_manager:
            self.log_manager.add_log_entry(message)
        
    def save_log(self, auto_save=False):
        """Save log"""
        try:
            if not self.log_manager:
                sound_type = "Engine Sound" if self.engine_radio.isChecked() else "Event Sound"
                self.log_manager = LogManager(sound_type)
                
                # Add current log text to log manager
                log_content = self.log_text.toPlainText()
                for line in log_content.split('\n'):
                    if line.strip():
                        self.log_manager.add_log_entry(line.strip())
            
            # Save as CSV file
            log_filename, is_manual = self.log_manager.save_log_to_csv(manual_save=not auto_save)
            
            if is_manual:  # Show popup only for manual save
                QMessageBox.information(self, "Save Complete", f"Log saved as: {log_filename}")
            else:  # For auto-save, only show in log (already handled in append_log)
                pass
                
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save log: {str(e)}")
        
    def show_sound_info_dialog(self, wav_files, start_addresses, sound_positions):
        """Show sound info dialog (engine sound only)"""
        dialog = AddressSettingDialog(wav_files, start_addresses, sound_positions, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # When dialog is closed normally
            updated_positions = dialog.get_sound_positions()
            self._log_engine_sound_positions(wav_files, start_addresses, updated_positions)
            
            # Continue engine processing in ProcessingThread
            self.processing_thread.complete_engine_processing(updated_positions)
        else:
            # If dialog is cancelled, finish thread
            self.processing_thread.finished.emit()
    
    def _log_engine_sound_positions(self, wav_files, start_addresses, sound_positions):
        """Output engine sound position info to log"""
        self.append_log("\n" + "< Engine Sound Position Information >")
        self.append_log("-" * LOG_WIDTH)
        self.append_log(f"{'Position'.center(20)}|{'Wave File'.center(60)}")
        self.append_log("-" * LOG_WIDTH)
        
        position_labels = [
            "Sound F1 ", "Sound F2 ", "Sound F3 ",
            "Sound S1 ", "Sound S2 ", "Sound S3 ",
            "Sound C1 ", "Sound C2 ",
            "Sound R1 ", "Sound R2 "
        ]
        
        for i, (label, position) in enumerate(zip(position_labels, sound_positions)):
            if position.upper() != "FFFFFFFF":
                # Find matching WAV file for this address
                position_addr = int(position, 16)
                wave_file = "Not found"
                for j, start_addr in enumerate(start_addresses):
                    if start_addr == position_addr:
                        wave_file = wav_files[j]
                        break
            else:
                wave_file = "Not assigned"
            
            self.append_log(f"{label.ljust(20)}| {wave_file.ljust(60)}")
        
        self.append_log("-" * LOG_WIDTH)
        
    def handle_no_wav_files(self):
        """Handle case when no WAV files are found"""
        QMessageBox.warning(self, "No WAV Files", "No WAV files found in the selected folder.")
        self.enable_buttons() 
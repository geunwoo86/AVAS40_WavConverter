"""
=========================================================================================
📌 파일명:      main_window.py
📌 설명:        AVAS40 WavConverter 메인 윈도우 클래스
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
=========================================================================================
"""

import os
import csv
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QRadioButton,
                            QTextEdit, QFileDialog, QMessageBox, QAction, QDialog)
from config import app_settings
from utils import TOOL_VERSION, LOG_WIDTH
from processing import ProcessingThread, AddressSettingDialog
from dialogs import SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"AVAS40 WAV to Binary Converter v{TOOL_VERSION}")
        self.setGeometry(100, 100, 800, 600)
        
        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)
        
        # 메뉴바 설정
        self.setup_menu_bar()
        
        # 메인 위젯과 레이아웃 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 입력 폴더 선택 그룹
        input_group = QGroupBox("Input Settings")
        input_layout = QGridLayout()
        
        self.input_folder_edit = QLineEdit()
        self.input_folder_edit.setAcceptDrops(True)  # 드래그 앤 드롭 활성화
        self.input_folder_edit.dragEnterEvent = self.dragEnterEvent
        self.input_folder_edit.dropEvent = self.dropEvent
        
        self.browse_button = QPushButton("Open Folder")
        self.browse_button.clicked.connect(self.browse_folder)
        
        input_layout.addWidget(QLabel("Input Folder:"), 0, 0)
        input_layout.addWidget(self.input_folder_edit, 0, 1)
        input_layout.addWidget(self.browse_button, 0, 2)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 설정 그룹
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QGridLayout()
        
        # 압축 레벨
        self.compression_combo = QComboBox()
        self.compression_combo.addItems([str(x) for x in range(11)])
        self.compression_combo.setCurrentText("8")
        self.compression_combo.setEnabled(False)  # 비활성화
        
        # 블록 크기
        self.block_size_combo = QComboBox()
        self.block_size_combo.addItems(["128", "256", "512", "1024", "2048", "4096"])
        self.block_size_combo.setCurrentText("512")
        self.block_size_combo.setEnabled(False)  # 비활성화
        
        settings_layout.addWidget(QLabel("Compression:"), 0, 0)
        settings_layout.addWidget(self.compression_combo, 0, 1)
        settings_layout.addWidget(QLabel("Block Size:"), 0, 2)
        settings_layout.addWidget(self.block_size_combo, 0, 3)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 사운드 타입 그룹
        sound_group = QGroupBox("Sound Type")
        sound_layout = QHBoxLayout()
        
        self.engine_radio = QRadioButton("Engine")
        self.event_radio = QRadioButton("Event")
        self.engine_radio.setChecked(True)
        self.engine_radio.toggled.connect(self.update_fields)
        
        sound_layout.addWidget(self.engine_radio)
        sound_layout.addWidget(self.event_radio)
        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)
        
        # 주소 설정 그룹
        address_group = QGroupBox("Address Settings")
        address_layout = QGridLayout()
        
        self.start_address_edit = QLineEdit("10118000")
        
        address_layout.addWidget(QLabel("Start Address (Hex):"), 0, 0)
        address_layout.addWidget(self.start_address_edit, 0, 1)
        
        address_group.setLayout(address_layout)
        layout.addWidget(address_group)
        
        # 버튼 그룹
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.start_processing)
        self.save_button = QPushButton("Save Log")
        self.save_button.clicked.connect(self.save_log)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)
        
        # 로그 텍스트 영역
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 처리 스레드
        self.processing_thread = ProcessingThread()
        self.processing_thread.log_message.connect(self.append_log)
        self.processing_thread.finished.connect(self.enable_buttons)
        self.processing_thread.save_log.connect(lambda: self.save_log(auto_save=True))
        self.processing_thread.show_info_dialog.connect(self.show_sound_info_dialog)
        self.processing_thread.no_wav_files.connect(self.handle_no_wav_files)
        
        # 초기 상태 설정
        self.update_fields()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.input_folder_edit.setText(path)
            else:
                QMessageBox.warning(self, "Warning", "Please drop a folder, not a file.")
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with WAV files")
        if folder:
            self.input_folder_edit.setText(folder)
            
    def update_fields(self):
        if self.engine_radio.isChecked():
            self.start_address_edit.setText("10118000")
            self.start_address_edit.setEnabled(False)
        else:
            self.start_address_edit.setText("00001000")
            self.start_address_edit.setEnabled(True)
            
    def append_log(self, message):
        self.log_text.append(message)
        
    def enable_buttons(self):
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.input_folder_edit.setEnabled(True)
        self.engine_radio.setEnabled(True)
        self.event_radio.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.update_fields()
        
    def disable_buttons(self):
        self.start_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.input_folder_edit.setEnabled(False)
        self.start_address_edit.setEnabled(False)
        self.engine_radio.setEnabled(False)
        self.event_radio.setEnabled(False)
        self.browse_button.setEnabled(False)
        
    def start_processing(self):
        input_folder = self.input_folder_edit.text()
        if not input_folder:
            QMessageBox.warning(self, "Warning", "No input folder selected. Please choose a folder and try again.")
            return
            
        self.disable_buttons()
        self.log_text.clear()
        
        self.processing_thread.set_parameters(
            input_folder,
            self.compression_combo.currentText(),
            self.block_size_combo.currentText(),
            "Engine Sound" if self.engine_radio.isChecked() else "Event Sound",
            self.start_address_edit.text(),
            "864.00"  # 기본값으로 고정
        )
        
        self.processing_thread.start()
        
    def save_log(self, auto_save=False):
        # 현재 선택된 사운드 타입에 따라 폴더 분리
        if self.engine_radio.isChecked():
            output_folder = os.path.join(app_settings.get_output_base_path(), "Output", "EngineSound")
        else:  # Event Sound
            output_folder = os.path.join(app_settings.get_output_base_path(), "Output", "EventSound")
        log_folder = os.path.join(output_folder, "log")
        os.makedirs(log_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{timestamp}_log.csv"
        log_filepath = os.path.join(log_folder, log_filename)

        log_content = self.log_text.toPlainText()
        if not log_content:
            if not auto_save:  # 수동 저장 시에만 경고 표시
                QMessageBox.warning(self, "Warning", "No log content to save.")
            return

        with open(log_filepath, "w", newline='', encoding="utf-8-sig") as csv_file:
            csv_writer = csv.writer(csv_file)
            for line in log_content.split("\n"):
                if "|" in line:
                    columns = [col.strip() for col in line.split("|")]
                    csv_writer.writerow(columns)
                else:
                    csv_writer.writerow([line])
                    
        if auto_save:
            # 자동 저장 시: 로그창에 파일명 표시, 팝업 없음
            self.append_log(f"Log saved: {log_filename}")
        else:
            # 수동 저장 시: 기존 팝업창 유지, 로그에 메시지 출력하지 않음
            QMessageBox.information(self, "Success", f"Log has been saved successfully.\nSaved location: {log_filepath}")

    def handle_no_wav_files(self):
        QMessageBox.warning(self, "Warning", "No WAV files found in the selected folder.")
        self.enable_buttons()

    def show_sound_info_dialog(self, wav_files, start_addresses, sound_positions):
        try:
            dialog = AddressSettingDialog(wav_files, start_addresses, sound_positions, self)
            if dialog.exec_() == QDialog.Accepted and not dialog.has_error:
                # 팝업창이 닫힌 후 HEX 데이터 병합 진행
                output_folder = os.path.join(app_settings.get_output_base_path(), "Output", "EngineSound")
                output_hex_file = os.path.join(output_folder, "MergedEngineSound.hex")
                
                self.append_log("\n" + "=" * LOG_WIDTH)
                self.append_log("[ File Creation ]")
                self.append_log("=" * LOG_WIDTH)
                
                # 수정된 sound positions 값으로 데이터 병합
                self.processing_thread.merge_hex_data(
                    self.processing_thread.hex_data_list,
                    output_folder,
                    dialog.get_sound_positions()
                )
                
                # HEX 데이터 병합이 완료된 후에 로그 저장
                self.save_log(auto_save=True)
                
                self.append_log("\nProcessing completed successfully.")
                self.enable_buttons()
        except Exception as e:
            self.append_log(f"Processing failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error in merging hex files: {str(e)}")
            self.enable_buttons()

    def setup_menu_bar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # Settings 메뉴
        settings_menu = menubar.addMenu('Settings')
        
        # Output Path Settings 액션
        output_path_action = QAction('Output Path Settings', self)
        output_path_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(output_path_action)
    
    def open_settings_dialog(self):
        """설정 다이얼로그 열기"""
        dialog = SettingsDialog(self)
        dialog.exec_() 
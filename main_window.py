"""
=========================================================================================
📌 파일명:      main_window.py
📌 설명:        AVAS40 WavConverter 메인 윈도우 클래스 (리팩토링됨)
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
from utils import TOOL_VERSION, LOG_WIDTH, AudioConstants, UIConstants
from processing import ProcessingThread, AddressSettingDialog
from dialogs import SettingsDialog
from file_manager import LogManager, OutputPathManager

class MainWindow(QMainWindow):
    """메인 윈도우 클래스 (리팩토링됨)"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"AVAS40 Sound Converter v{TOOL_VERSION}")
        self.setGeometry(100, 100, UIConstants.MAIN_WINDOW_WIDTH, UIConstants.MAIN_WINDOW_HEIGHT)
        
        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)
        
        # 메뉴바 설정
        self.setup_menu_bar()
        
        # UI 구성
        self._setup_ui()
        
        # 처리 객체들 초기화
        self._init_processing_objects()
        
        # 초기 상태 설정
        self.update_fields()
        
    def _setup_ui(self):
        """UI 구성"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 입력 폴더 선택 그룹
        layout.addWidget(self._create_input_group())
        
        # 설정 그룹
        layout.addWidget(self._create_settings_group())
        
        # 사운드 타입 그룹
        layout.addWidget(self._create_sound_type_group())
        
        # 주소 설정 그룹
        layout.addWidget(self._create_address_group())
        
        # 버튼 그룹
        layout.addLayout(self._create_button_layout())
        
        # 로그 텍스트 영역
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
    
    def _create_input_group(self) -> QGroupBox:
        """입력 폴더 선택 그룹 생성"""
        input_group = QGroupBox("Input Settings")
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
        """설정 그룹 생성"""
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QGridLayout()
        
        # 압축 레벨
        self.compression_combo = QComboBox()
        self.compression_combo.addItems([str(x) for x in range(11)])
        self.compression_combo.setCurrentText(AudioConstants.DEFAULT_COMPRESSION)
        self.compression_combo.setEnabled(False)  # 비활성화
        
        # 블록 크기
        self.block_size_combo = QComboBox()
        self.block_size_combo.addItems(["128", "256", "512", "1024", "2048", "4096"])
        self.block_size_combo.setCurrentText(AudioConstants.DEFAULT_BLOCK_SIZE)
        self.block_size_combo.setEnabled(False)  # 비활성화
        
        settings_layout.addWidget(QLabel("Compression:"), 0, 0)
        settings_layout.addWidget(self.compression_combo, 0, 1)
        settings_layout.addWidget(QLabel("Block Size:"), 0, 2)
        settings_layout.addWidget(self.block_size_combo, 0, 3)
        
        settings_group.setLayout(settings_layout)
        return settings_group
    
    def _create_sound_type_group(self) -> QGroupBox:
        """사운드 타입 그룹 생성"""
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
        """주소 설정 그룹 생성"""
        address_group = QGroupBox("Address Settings")
        address_layout = QGridLayout()
        
        self.start_address_edit = QLineEdit(AudioConstants.DEFAULT_START_ADDRESS)
        
        address_layout.addWidget(QLabel("Start Address (Hex):"), 0, 0)
        address_layout.addWidget(self.start_address_edit, 0, 1)
        
        address_group.setLayout(address_layout)
        return address_group
    
    def _create_button_layout(self) -> QHBoxLayout:
        """버튼 레이아웃 생성"""
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.start_processing)
        self.save_button = QPushButton("Save Log")
        self.save_button.clicked.connect(self.save_log)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.save_button)
        return button_layout
    
    def _init_processing_objects(self):
        """처리 객체들 초기화"""
        # 처리 스레드
        self.processing_thread = ProcessingThread()
        self.processing_thread.log_message.connect(self.append_log)
        self.processing_thread.finished.connect(self.enable_buttons)
        self.processing_thread.save_log.connect(lambda: self.save_log(auto_save=True))
        self.processing_thread.show_info_dialog.connect(self.show_sound_info_dialog)
        self.processing_thread.no_wav_files.connect(self.handle_no_wav_files)
        
        # 로그 매니저는 처리 시작 시 초기화
        self.log_manager = None
        
    def dragEnterEvent(self, event):
        """드래그 앤 드롭 이벤트 처리"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """드롭 이벤트 처리"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.input_folder_edit.setText(path)
            else:
                QMessageBox.warning(self, "Warning", "Please drop a folder, not a file.")
        
    def browse_folder(self):
        """폴더 선택 다이얼로그"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with WAV files")
        if folder:
            self.input_folder_edit.setText(folder)
    
    def setup_menu_bar(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        settings_menu = menubar.addMenu('Settings')
        output_path_action = QAction('Output Path Settings', self)
        output_path_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(output_path_action)

    def open_settings_dialog(self):
        """설정 다이얼로그 열기"""
        dialog = SettingsDialog(self)
        dialog.exec_()
        
    def update_fields(self):
        """사운드 타입에 따른 필드 업데이트"""
        is_engine = self.engine_radio.isChecked()
        
        if is_engine:
            # Engine 타입: 주소 "10118000" + 비활성화
            self.start_address_edit.setText("10118000")
            self.start_address_edit.setEnabled(False)
        else:
            # Event 타입: 주소 "00001000" + 활성화
            self.start_address_edit.setText("00001000")
            self.start_address_edit.setEnabled(True)
        
    def start_processing(self):
        """처리 시작"""
        if not self._validate_input():
            return
        
        # 로그 매니저 초기화
        sound_type = "Engine Sound" if self.engine_radio.isChecked() else "Event Sound"
        self.log_manager = LogManager(sound_type)
        
        # UI 비활성화
        self.disable_buttons()
        
        # 로그 초기화
        self.log_text.clear()
        
        # 처리 매개변수 설정
        self._set_processing_parameters()
        
        # 처리 시작
        self.processing_thread.start()
        
    def _validate_input(self) -> bool:
        """입력 유효성 검사"""
        input_folder = self.input_folder_edit.text()
        if not input_folder:
            QMessageBox.warning(self, "Warning", "Please select an input folder.")
            return False
            
        if not os.path.exists(input_folder):
            QMessageBox.warning(self, "Warning", "Selected folder does not exist.")
            return False
            
        # 주소 유효성 검사 (Event Sound인 경우만)
        if self.event_radio.isChecked():
            try:
                int(self.start_address_edit.text(), 16)
            except ValueError:
                QMessageBox.warning(self, "Warning", "Please enter a valid hexadecimal address.")
                return False
        
        return True
    
    def _set_processing_parameters(self):
        """처리 매개변수 설정"""
        input_folder = self.input_folder_edit.text()
        compression_level = self.compression_combo.currentText()
        block_size = self.block_size_combo.currentText()
        sound_type = "Engine Sound" if self.engine_radio.isChecked() else "Event Sound"
        hex_start_address = self.start_address_edit.text()
        hex_file_size_kb = "864.00"  # 기본값
        
        self.processing_thread.set_parameters(
            input_folder, compression_level, block_size, 
            sound_type, hex_start_address, hex_file_size_kb
        )
        
    def disable_buttons(self):
        """버튼 비활성화"""
        self.start_button.setEnabled(False)
        self.save_button.setEnabled(False)
        
    def enable_buttons(self):
        """버튼 활성화"""
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(True)
        
    def append_log(self, message):
        """로그 메시지 추가"""
        self.log_text.append(message)
        # 로그 매니저에도 추가
        if self.log_manager:
            self.log_manager.add_log_entry(message)
        
    def save_log(self, auto_save=False):
        """로그 저장"""
        try:
            if not self.log_manager:
                sound_type = "Engine Sound" if self.engine_radio.isChecked() else "Event Sound"
                self.log_manager = LogManager(sound_type)
                
                # 현재 로그 텍스트를 로그 매니저에 추가
                log_content = self.log_text.toPlainText()
                for line in log_content.split('\n'):
                    if line.strip():
                        self.log_manager.add_log_entry(line.strip())
            
            # CSV 파일로 저장
            log_filename, is_manual = self.log_manager.save_log_to_csv(manual_save=not auto_save)
            
            if is_manual:  # 수동 저장 시에만 팝업 표시
                QMessageBox.information(self, "Save Complete", f"Log saved as: {log_filename}")
            else:  # 자동 저장 시 로그창에만 표시 (이미 append_log에서 처리됨)
                pass
                
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save log: {str(e)}")
        
    def show_sound_info_dialog(self, wav_files, start_addresses, sound_positions):
        """사운드 정보 다이얼로그 표시 (엔진 사운드만)"""
        dialog = AddressSettingDialog(wav_files, start_addresses, sound_positions, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # 다이얼로그가 정상적으로 닫혔을 때의 처리
            updated_positions = dialog.get_sound_positions()
            self._log_engine_sound_positions(wav_files, start_addresses, updated_positions)
            
            # ProcessingThread에서 엔진 처리 완료 계속 진행
            self.processing_thread.complete_engine_processing(updated_positions)
        else:
            # 다이얼로그가 취소된 경우 스레드 종료
            self.processing_thread.finished.emit()
    
    def _log_engine_sound_positions(self, wav_files, start_addresses, sound_positions):
        """엔진 사운드 포지션 정보를 로그에 출력"""
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
                # 매칭되는 WAV 파일 찾기
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
        """WAV 파일이 없을 때 처리"""
        QMessageBox.warning(self, "No WAV Files", "No WAV files found in the selected folder.")
        self.enable_buttons() 
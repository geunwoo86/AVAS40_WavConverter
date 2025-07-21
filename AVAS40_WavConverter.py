"""
=========================================================================================
📌 파일명:      AVAS40_WavToHexConverter.py
📌 설명:        wav 파일을 flac file로 encoding 후 hex file로 변환 및 통합하는 기능을 지원한다.
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-05-29
📌 버전:        1.00
=========================================================================================
📌 변경 이력
-----------------------------------------------------------------------------------------
날짜          | 작성자        | 버전   | 변경 내용
-----------------------------------------------------------------------------------------
2025-05-29   | Geunwoo Lee   | 1.00  | 최초 작성

=========================================================================================
📌 사용 방법:
    - 배포 메뉴얼 참조
=========================================================================================
📌 의존성:
    - Python ver 3.12.3
    - 필수 추가 파일 : flac.exe, libFLAC.dll
    - PyQt5
=========================================================================================
"""

import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QLineEdit, QPushButton, QComboBox, QRadioButton,
                            QTextEdit, QFileDialog, QMessageBox, QGroupBox, QGridLayout,
                            QTableWidget, QTableWidgetItem, QDialog, QCheckBox, QMenuBar, QAction)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRegExp
from PyQt5.QtGui import QRegExpValidator
from intelhex import IntelHex
from datetime import datetime
import csv
import sys
import wave
import io
import json

LOG_WIDTH = 100
TOOL_VERSION = "1.00"

def get_exe_directory():
    """exe 파일이 있는 디렉토리를 반환"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 실행된 경우
        return os.path.dirname(sys.executable)
    else:
        # 스크립트로 실행된 경우
        return os.path.dirname(os.path.abspath(__file__))

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

class ProcessingThread(QThread):
    finished = pyqtSignal()
    log_message = pyqtSignal(str)
    save_log = pyqtSignal()
    show_info_dialog = pyqtSignal(list, list, list)
    no_wav_files = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_folder = ""
        self.compression_level = "8"
        self.block_size = "512"
        self.sound_type = "Engine Sound"
        self.hex_start_address = "10118000"
        self.hex_file_size_kb = "864.00"
        self.hex_data_list = []
        self.output_hex_file = ""
        self.wav_files = []
        self.start_addresses = []
        
    def set_parameters(self, input_folder, compression_level, block_size, sound_type, hex_start_address, hex_file_size_kb):
        self.input_folder = input_folder
        self.compression_level = compression_level
        self.block_size = block_size
        self.sound_type = sound_type
        self.hex_start_address = hex_start_address
        self.hex_file_size_kb = hex_file_size_kb
        
    def run(self):
        try:
            self.log_message.emit("Starting processing")
                   
            self.wav_files = [f for f in os.listdir(self.input_folder) if f.endswith(".wav")]
            
            if not self.wav_files:
                self.no_wav_files.emit()
                self.finished.emit()
                return
            
            # 사운드 타입에 따라 폴더 분리
            if self.sound_type == "Engine Sound":
                output_folder = os.path.join(app_settings.get_output_base_path(), "Output", "EngineSound")
            else:  # Event Sound
                output_folder = os.path.join(app_settings.get_output_base_path(), "Output", "EventSound")
            os.makedirs(output_folder, exist_ok=True)
                
            # WAV → FLAC 변환 및 HEX 변환
            self.log_message.emit("\n" + "=" * LOG_WIDTH)
            self.log_message.emit("[ File Conversion ]")
            self.log_message.emit("=" * LOG_WIDTH)
            
            self.hex_data_list = []
            self.start_addresses = []
            
            # 시작 주소 계산 (사운드 타입에 따라 다름)
            base_address = int(self.hex_start_address, 16)
            if self.sound_type == "Engine Sound":
                current_address = base_address + 44  # Magic key(4) + Sound positions(40)
            else:  # Event Sound
                current_address = base_address + 8   # Event header (8 bytes)
            
            hex_file_addresses = {}  # 파일별 주소 정보 저장
            
            for wav_file in self.wav_files:
                wav_file_path = os.path.join(self.input_folder, wav_file)
                try:
                    hex_data = self.process_wav_to_hex_data(wav_file_path)
                    self.hex_data_list.append(hex_data)
                    self.start_addresses.append(current_address)
                    
                    # 파일별 주소 정보 저장
                    hex_file_addresses[wav_file] = (current_address, len(hex_data))
                    
                    current_address += len(hex_data)
                    # 4바이트 정렬
                    if current_address % 4 != 0:
                        current_address += 4 - (current_address % 4)
                    self.log_message.emit(f"Conversion completed : {os.path.basename(wav_file)}")
                except Exception as e:
                    self.log_message.emit(f"Conversion Failed : {os.path.basename(wav_file)} : {str(e)}")
                    raise e  # 예외 발생 시 처리를 중단하고 상위로 전파
            
            if self.sound_type == "Engine Sound":
                # 사운드 정보 다이얼로그 표시
                sound_positions = ["FFFFFFFF"] * 10
                self.show_info_dialog.emit(self.wav_files, self.start_addresses, sound_positions)
            else:  # Event Sound
                # Event Sound의 경우 바로 HEX 파일 생성
                output_hex_file = os.path.join(output_folder, "MergedEventSound.hex")
                
                # 파일 정보 로그 출력
                self.log_message.emit("\n" + "-" * LOG_WIDTH)
                self.log_message.emit(f"{'File Name':<50} | {'Start Address':>13} | {'Data Length':>11}")
                self.log_message.emit("-" * LOG_WIDTH)
                for wav_file, (start, length) in hex_file_addresses.items():
                    file_name = os.path.basename(wav_file)
                    # 파일명이 너무 길면 자르고 "..." 추가
                    if len(file_name) > 47:
                        file_name = file_name[:44] + "..."
                    file_name_formatted = f"{file_name:<50}"
                    start_address = f"0x{start:08X}"
                    data_length = f"0x{length:08X}"
                    self.log_message.emit(f"{file_name_formatted} | {start_address:>13} | {data_length:>11}")
                self.log_message.emit("-" * LOG_WIDTH)
                
                # 파일 생성 (내부적으로만 사용)
                self.log_message.emit("=" * LOG_WIDTH)
                self.log_message.emit("[ File Creation ]")
                self.log_message.emit("=" * LOG_WIDTH)
                self.merge_hex_data(self.hex_data_list, output_folder)
                self.save_log.emit()
                self.log_message.emit("\nProcessing completed successfully.")
                self.finished.emit()
            
        except Exception as e:
            self.log_message.emit(f"Error in processing thread: {str(e)}")
            self.finished.emit()
        
    def process_wav_to_hex_data(self, wav_file_path):
        project_dir = os.getcwd()
        flac_executable = os.path.join(project_dir, "flac.exe")
        
        # 임시 FLAC 파일 생성
        temp_flac_file = os.path.normpath(os.path.join(os.path.dirname(wav_file_path), 
                                                      os.path.splitext(os.path.basename(wav_file_path))[0] + '.flac'))
        
        try:
            # WAV 파일의 샘플링 레이트 확인
            with wave.open(wav_file_path, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()
                frames = wav_file.readframes(n_frames)
                
                # 48kHz인 경우 24kHz로 다운샘플링
                if sample_rate == 48000:
                    #self.log_message.emit(f"Downsampling {os.path.basename(wav_file_path)} from 48kHz to 24kHz")
                    
                    # 2개 중 1개 샘플만 선택 (다운샘플링)
                    downsampled_frames = bytearray()
                    for i in range(0, len(frames), sample_width * n_channels * 2):
                        downsampled_frames.extend(frames[i:i + sample_width * n_channels])
                    
                    # 다운샘플링된 데이터를 임시 WAV 파일로 저장하지 않고 바로 FLAC 변환
                    temp_wav_data = io.BytesIO()
                    with wave.open(temp_wav_data, 'wb') as out_wav:
                        out_wav.setnchannels(n_channels)
                        out_wav.setsampwidth(sample_width)
                        out_wav.setframerate(24000)
                        out_wav.writeframes(downsampled_frames)
                    
                    # 임시 WAV 데이터를 FLAC 변환
                    flac_command = [
                        f'"{flac_executable}"',
                        "--no-padding",
                        f"-{self.compression_level}",
                        f"--blocksize={self.block_size}",
                        "-",  # stdin에서 입력 받음
                        "-o", f'"{temp_flac_file}"'
                    ]
                    
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                    process = subprocess.Popen(" ".join(flac_command), 
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE, 
                                            startupinfo=startupinfo)
                    process.communicate(input=temp_wav_data.getvalue())
                else:
                    # 24kHz 이면 원본 파일 사용
                    flac_command = [
                        f'"{flac_executable}"',
                        "--no-padding",
                        f"-{self.compression_level}",
                        f"--blocksize={self.block_size}",
                        f'"{wav_file_path}"'
                    ]
                    
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                    subprocess.run(" ".join(flac_command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
            
            # FLAC 데이터 읽기
            flac_size = os.path.getsize(temp_flac_file)
            
            ih = IntelHex()
            
            with open(temp_flac_file, 'rb') as f:
                flac_data = f.read()
                
            ih[0x0000] = flac_size & 0xFF
            ih[0x0001] = (flac_size >> 8) & 0xFF
            ih[0x0002] = (flac_size >> 16) & 0xFF
            ih[0x0003] = (flac_size >> 24) & 0xFF
            
            if self.sound_type == "Engine Sound":
                file_name = os.path.basename(wav_file_path).ljust(80, '\x00')
                for i, c in enumerate(file_name.encode('utf-8')):
                    ih[0x0004 + i] = c
                for i, byte in enumerate(flac_data):
                    ih[0x0054 + i] = byte
            else:
                for i, byte in enumerate(flac_data):
                    ih[0x0004 + i] = byte
                    
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_flac_file):
                os.remove(temp_flac_file)
        
        return ih
        
    def merge_hex_data(self, hex_data_list, output_folder, sound_positions=None):
        ih = IntelHex()
        start_address = int(self.hex_start_address, 16)
        current_address = start_address
        
        if self.sound_type == "Event Sound":
            for _ in range(8):
                ih[current_address] = 0xFF
                current_address += 1
                
            for temp_ih in hex_data_list:
                start_addr = current_address
                data_length = len(temp_ih)
                
                for address in range(temp_ih.minaddr(), temp_ih.maxaddr() + 1):
                    ih[current_address] = temp_ih[address]
                    current_address += 1
                    
                padding = current_address % 4
                if padding != 0:
                    padding_to_add = 4 - padding
                    for _ in range(padding_to_add):
                        ih[current_address] = 0xFF
                        current_address += 1
                        
            # Event Sound 모드에서 hex file 사이즈 출력
            hex_file_size = current_address - start_address
            self.log_message.emit(f"HEX file size: {hex_file_size:,} bytes ({hex_file_size/1024:.2f} KB)")
                        
        elif self.sound_type == "Engine Sound":
            # Magic key
            magic_key = 0x5AA55AA5
            ih[current_address] = magic_key & 0xFF
            ih[current_address + 1] = (magic_key >> 8) & 0xFF
            ih[current_address + 2] = (magic_key >> 16) & 0xFF
            ih[current_address + 3] = (magic_key >> 24) & 0xFF
            
            # Sound positions
            current_address += 4
            for position in sound_positions:
                pos_value = int(position, 16)
                ih[current_address] = pos_value & 0xFF
                ih[current_address + 1] = (pos_value >> 8) & 0xFF
                ih[current_address + 2] = (pos_value >> 16) & 0xFF
                ih[current_address + 3] = (pos_value >> 24) & 0xFF
                current_address += 4
                
            # Sound data
            total_flac_size = 0
            for temp_ih in hex_data_list:
                # FLAC 데이터 크기 계산 (헤더 4바이트 제외)
                flac_size = (temp_ih[0x0000] | (temp_ih[0x0001] << 8) | (temp_ih[0x0002] << 16) | (temp_ih[0x0003] << 24))
                total_flac_size += flac_size
                
                for address in range(temp_ih.minaddr(), temp_ih.maxaddr() + 1):
                    ih[current_address] = temp_ih[address]
                    current_address += 1
                    
                padding = current_address % 4
                if padding != 0:
                    padding_to_add = 4 - padding
                    for _ in range(padding_to_add):
                        ih[current_address] = 0xFF
                        current_address += 1
                        
            hex_file_size_bytes = int(float(self.hex_file_size_kb) * 1024)
            while current_address < (start_address + hex_file_size_bytes):
                ih[current_address] = 0xFF
                current_address += 1
        
        if self.sound_type == "Engine Sound":
            # BIN 파일 생성
            output_bin_file = os.path.join(output_folder, 'MergedEngineSound.bin')
            with open(output_bin_file, 'wb') as f:
                for address in range(ih.minaddr(), ih.maxaddr() + 1):
                    f.write(bytes([ih[address]]))
            
            header_file = os.path.join(output_folder, 'EngineSound_VARIANT.h')
            self.save_hex_as_header(ih, header_file)
            
            # FLAC 파일들의 총 데이터 크기 출력
            self.log_message.emit(f"Total data size: {total_flac_size:,} bytes")
            
            self.log_message.emit(f"Created BIN file: {os.path.basename(output_bin_file)}")
            self.log_message.emit(f"Created HEADER file: {os.path.basename(header_file)}")
        else:  # Event Sound
            # HEX 파일 생성
            output_hex_file = os.path.join(output_folder, 'MergedEventSound.hex')
            ih.write_hex_file(output_hex_file, write_start_addr=False)
            
            self.log_message.emit(f"Created HEX file: {os.path.basename(output_hex_file)}")
        
    def save_hex_as_header(self, ih, header_file):
        raw_data = bytearray()
        
        for address in range(ih.minaddr(), ih.maxaddr() + 1):
            raw_data.append(ih[address])
            
        with open(header_file, 'w') as f:
            f.write("#ifndef _SOUND_DATA_H_\n")
            f.write("#define _SOUND_DATA_H_\n\n")
            f.write(f"const unsigned char sound_data[{len(raw_data)}] = {{\n")
            
            # 16개씩 데이터를 정렬하여 출력
            for i in range(0, len(raw_data), 16):
                line = "    "  # 들여쓰기
                for j in range(16):
                    if i + j < len(raw_data):
                        line += f"0x{raw_data[i + j]:02X}"
                        if i + j < len(raw_data) - 1:  # 마지막 데이터가 아닌 경우
                            line += ", "
                        else:  # 마지막 데이터인 경우
                            line += " "
                    else:  # 마지막 줄에서 16개 미만인 경우
                        line += "    "  # 빈 공간 채우기
                
                f.write(line + "\n")
            
            f.write("};\n\n")
            f.write("#endif //_SOUND_DATA_H_\n")

class SoundInfoDialog(QDialog):
    def __init__(self, wav_files, start_addresses, sound_positions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sound Information")
        self.main_window = parent  # 부모 윈도우 참조 저장
        self.wav_files = wav_files  # WAV 파일 목록 저장
        self.start_addresses = start_addresses  # 시작 주소 목록 저장
        self.has_error = False  # 에러 상태 플래그 추가
        
        # 창 크기를 WAV 파일 수에 따라 동적으로 조정
        base_height = 100
        row_height = 40
        table_height = len(wav_files) * row_height + 30  # 헤더 높이 포함
        self.setGeometry(150, 150, 1000, base_height + table_height)
        
        layout = QVBoxLayout()
        
        # 파일 정보 테이블
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["WAV File", "Start Address"])
        table.setRowCount(len(wav_files))
        
        # 컬럼 너비 설정
        table.setColumnWidth(0, 600)  # WAV File 컬럼 너비
        table.setColumnWidth(1, 200)  # Start Address 컬럼 너비
        
        # 테이블 높이 설정
        table.setFixedHeight(table_height)
        
        self.start_address_items = []  # Start Address 아이템 저장
        for i, (wav_file, addr) in enumerate(zip(wav_files, start_addresses)):
            # WAV File
            table.setItem(i, 0, QTableWidgetItem(wav_file))
            
            # Start Address (0x 제거)
            addr_item = QTableWidgetItem(f"{addr:08X}")
            addr_item.setFlags(addr_item.flags() & ~Qt.ItemIsEditable)  # 수정 불가능하게 설정
            table.setItem(i, 1, addr_item)
            self.start_address_items.append(addr_item)
            
        layout.addWidget(table)
        
        # Engine Sound Positions 정보
        if sound_positions:
            positions_group = QGroupBox("Engine Sound Positions")
            positions_layout = QGridLayout()
            
            position_labels = [
                "Sound F1 position:", "Sound F2 position:", "Sound F3 position:",
                "Sound S1 position:", "Sound S2 position:", "Sound S3 position:",
                "Sound C1 position:", "Sound C2 position:",
                "Sound R1 position:", "Sound R2 position:"
            ]
            
            self.position_edits = []  # 수정된 포지션 값을 저장할 리스트
            for i, (label_text, position) in enumerate(zip(position_labels, sound_positions)):
                label = QLabel(label_text)
                edit = QLineEdit(position)
                edit.setMaxLength(8)  # 8자리 16진수
                edit.setValidator(QRegExpValidator(QRegExp("[0-9A-Fa-f]{8}")))  # 16진수만 입력 가능
                self.position_edits.append(edit)
                positions_layout.addWidget(label, i, 0)
                positions_layout.addWidget(edit, i, 1)
                
            positions_group.setLayout(positions_layout)
            layout.addWidget(positions_group)
            
        # 확인 버튼
        done_button = QPushButton("Apply")
        done_button.clicked.connect(self.accept)
        layout.addWidget(done_button)
        
        self.setLayout(layout)
        
    def get_sound_positions(self):
        return [edit.text().upper() for edit in self.position_edits] if hasattr(self, 'position_edits') else []

    def accept(self):
        # Engine Sound Position 정보를 로그창에 출력
        if hasattr(self, 'position_edits'):
            # address 매치 검사를 위한 리스트
            unmatched_positions = []
            
            # 포지션 레이블과 값 출력
            position_labels = [
                "Sound F1 ", "Sound F2 ", "Sound F3 ",
                "Sound S1 ", "Sound S2 ", "Sound S3 ",
                "Sound C1 ", "Sound C2 ",
                "Sound R1 ", "Sound R2 "
            ]
            
            for i, (label, edit) in enumerate(zip(position_labels, self.position_edits)):
                position_value = edit.text().upper()
                if position_value != "FFFFFFFF":
                    # 입력된 주소를 16진수로 변환
                    try:
                        position_addr = int(position_value, 16)
                        # 해당 주소에 매칭되는 WAV 파일 찾기
                        wave_file = "Not found"
                        for j, start_addr in enumerate(self.start_addresses):
                            if start_addr == position_addr:
                                wave_file = self.wav_files[j]
                                break
                        if wave_file == "Not found":
                            unmatched_positions.append(label.strip())
                    except ValueError:
                        wave_file = "Invalid address"
                        unmatched_positions.append(label.strip())
            
            # 매치되지 않은 position이 있는 경우 에러 메시지만 출력
            if unmatched_positions:
                self.has_error = True
                error_msg = "Error: The following positions have unmatched addresses:\n"
                for pos in unmatched_positions:
                    error_msg += f"'- {pos}\n"
                error_msg += "\nPlease check the addresses and try again."
                self.main_window.append_log("\n" + error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                return  # 처리를 중단하고 다이얼로그를 닫지 않음
            else:
                self.has_error = False  # 모든 매칭이 완료되면 에러 상태 해제
                
                # 모든 매칭이 완료된 경우에만 표 출력
                self.main_window.append_log("\n" + "< Engine Sound Position Information >")
                self.main_window.append_log("-" * LOG_WIDTH)
                self.main_window.append_log(f"{'Position'.center(20)}|{'Wave File'.center(60)}")
                self.main_window.append_log("-" * LOG_WIDTH)
                
                for i, (label, edit) in enumerate(zip(position_labels, self.position_edits)):
                    position_value = edit.text().upper()
                    if position_value != "FFFFFFFF":
                        position_addr = int(position_value, 16)
                        wave_file = "Not found"
                        for j, start_addr in enumerate(self.start_addresses):
                            if start_addr == position_addr:
                                wave_file = self.wav_files[j]
                                break
                    else:
                        wave_file = "Not assigned"
                    
                    self.main_window.append_log(f"{label.ljust(20)}| {wave_file.ljust(60)}")
                
                self.main_window.append_log("-" * LOG_WIDTH)
        
        super().accept()
        
    def closeEvent(self, event):
        # 창이 닫힐 때 Done 버튼을 클릭한 것과 동일하게 처리
        self.accept()
        event.accept()

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
            dialog = SoundInfoDialog(wav_files, start_addresses, sound_positions, self)
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

class SettingsDialog(QDialog):
    """설정 다이얼로그 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setup_ui()
        self.setFixedSize(440, 180)  # 고정 크기로 설정
        
    def setup_ui(self):
        """설정 다이얼로그 UI 구성"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)  # 레이아웃 간격 줄이기
        layout.setContentsMargins(10, 10, 10, 10)  # 여백 줄이기
        
        # Current Output Path 그룹
        current_group = QGroupBox("Current Output Path")
        current_layout = QVBoxLayout()
        current_layout.setContentsMargins(8, 5, 8, 5)  # 그룹 내부 여백 줄이기
        
        self.current_path_display = QLabel()
        self.current_path_display.setWordWrap(True)  # 긴 경로 줄바꿈 허용
        current_layout.addWidget(self.current_path_display)
        current_group.setLayout(current_layout)
        layout.addWidget(current_group)
        
        # Change Output Path 그룹
        change_group = QGroupBox("Change Output Path")
        change_layout = QVBoxLayout()
        change_layout.setContentsMargins(8, 5, 8, 5)  # 그룹 내부 여백 줄이기
        change_layout.setSpacing(5)  # 그룹 내부 간격 줄이기
        
        # Output Path 입력 필드와 Browse 버튼
        path_layout = QHBoxLayout()
        path_layout.setSpacing(5)  # 수평 간격 줄이기
        path_layout.addWidget(QLabel("Output Path:"))
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)  # 읽기 전용으로 설정
        # 현재 설정된 경로를 표시
        current_path = app_settings.get_output_base_path()
        self.output_path_edit.setText(current_path)
        path_layout.addWidget(self.output_path_edit)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setMaximumWidth(80)  # 버튼 너비 제한
        self.browse_btn.clicked.connect(self.browse_output_path)
        path_layout.addWidget(self.browse_btn)
        
        change_layout.addLayout(path_layout)
        
        # Reset to Default 버튼
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self.reset_to_default)
        change_layout.addWidget(self.reset_btn)
        
        change_group.setLayout(change_layout)
        layout.addWidget(change_group)
        
        # Apply/Cancel 버튼
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # 버튼 간격 줄이기
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setMinimumWidth(80)  # 버튼 최소 너비 설정
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(80)  # 버튼 최소 너비 설정
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 초기 표시 업데이트
        self.update_current_path_display()
        
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
        
        if not new_path:
            QMessageBox.warning(self, "Warning", "Please enter a path.")
            return
        
        default_path = get_exe_directory()
        
        # 경로 존재 여부 및 쓰기 권한 확인
        if not os.path.isdir(new_path):
            QMessageBox.warning(self, "Warning", "The specified path does not exist.")
            return
        
        if not os.access(new_path, os.W_OK):
            QMessageBox.warning(self, "Warning", 
                              f"No write permission for directory: {new_path}")
            return
        
        # 설정 저장
        if new_path == default_path:
            app_settings.use_default_path = True
            app_settings.custom_output_path = ""
        else:
            app_settings.use_default_path = False
            app_settings.custom_output_path = new_path
            
        app_settings.save_settings()
        
        QMessageBox.information(self, "Information", "Output path has been successfully changed.")
        self.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
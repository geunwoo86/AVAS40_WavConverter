"""
=========================================================================================
📌 파일명:      processing.py  
📌 설명:        AVAS40 WavConverter 프로세싱 스레드와 관련 다이얼로그
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
=========================================================================================
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QGroupBox, 
                            QTableWidget, QTableWidgetItem, QLabel, QLineEdit, 
                            QPushButton, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator
from intelhex import IntelHex
from utils import (LOG_WIDTH, AudioConstants, UIConstants, AudioFileError, 
                  FlacConversionError, HexDataError, ProcessingError)
from audio_processor import AudioProcessor, HexMerger
from file_manager import FileManager, LogManager

class ProcessingThread(QThread):
    """오디오 파일 처리 스레드 (리팩토링된 버전)"""
    
    finished = pyqtSignal()
    log_message = pyqtSignal(str)
    save_log = pyqtSignal()
    show_info_dialog = pyqtSignal(list, list, list)
    no_wav_files = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_parameters()
        
    def _init_parameters(self):
        """매개변수 초기화"""
        self.input_folder = ""
        self.compression_level = AudioConstants.DEFAULT_COMPRESSION
        self.block_size = AudioConstants.DEFAULT_BLOCK_SIZE
        self.sound_type = "Engine Sound"
        self.hex_start_address = AudioConstants.DEFAULT_START_ADDRESS
        self.hex_file_size_kb = "864.00"
        
        # 처리 결과 데이터
        self.hex_data_list = []
        self.wav_files = []
        self.start_addresses = []
        
        # 처리 객체들
        self.audio_processor = None
        self.hex_merger = None
        self.file_manager = None
        self.log_manager = None
        
    def set_parameters(self, input_folder, compression_level, block_size, sound_type, hex_start_address, hex_file_size_kb):
        """처리 매개변수 설정"""
        self.input_folder = input_folder
        self.compression_level = compression_level
        self.block_size = block_size
        self.sound_type = sound_type
        self.hex_start_address = hex_start_address
        self.hex_file_size_kb = hex_file_size_kb
        
        # 처리 객체들 초기화
        self._init_processors()
        
    def _init_processors(self):
        """처리 객체들 초기화"""
        self.audio_processor = AudioProcessor(self.compression_level, self.block_size)
        self.hex_merger = HexMerger(self.sound_type, self.hex_start_address)
        self.file_manager = FileManager(self.sound_type)
        self.log_manager = LogManager(self.sound_type)
        
    def run(self):
        """메인 처리 로직"""
        try:
            self.log_message.emit("Starting processing")
            self.log_manager.add_log_entry("Processing started")
            
            # 1. WAV 파일 검색 및 검증
            if not self._find_and_validate_wav_files():
                return
            
            # 2. 출력 폴더 준비
            if not self._prepare_output_folder():
                return
            
            # 3. WAV → FLAC → HEX 변환
            if not self._convert_wav_files():
                return
            
            # 3.5. 파일 정보 로그 출력 (이벤트 사운드만)
            if self.sound_type == "Event Sound":
                self._log_file_info()
            
            # 4. 사운드 타입별 처리 분기
            if self.sound_type == "Engine Sound":
                # 엔진 사운드: AddressSettingDialog 표시 후 처리 계속
                self._show_engine_address_dialog()
            else:
                # 이벤트 사운드: 바로 병합/저장 진행
                if not self._merge_and_save_files():
                    return
                self._finalize_processing()
            
        except Exception as e:
            error_msg = f"Error in processing thread: {str(e)}"
            self.log_message.emit(error_msg)
            self.log_manager.add_log_entry(f"Error: {str(e)}")
            self.finished.emit()  # 에러 시에도 finished 시그널 발생
            
    def _find_and_validate_wav_files(self) -> bool:
        """WAV 파일 검색 및 검증"""
        try:
            if not os.path.exists(self.input_folder):
                raise ProcessingError(f"Input folder does not exist: {self.input_folder}")
                
            self.wav_files = [f for f in os.listdir(self.input_folder) if f.endswith(".wav")]
            
            if not self.wav_files:
                self.no_wav_files.emit()
                return False
                
            self.log_message.emit(f"Found {len(self.wav_files)} WAV files")
            self.log_manager.add_log_entry(f"Found {len(self.wav_files)} WAV files")
            return True
            
        except Exception as e:
            self.log_message.emit(f"Error finding WAV files: {str(e)}")
            self.log_manager.add_log_entry(f"Error finding WAV files: {str(e)}")
            return False
    
    def _prepare_output_folder(self) -> bool:
        """출력 폴더 준비"""
        try:
            output_folder = self.file_manager.ensure_output_folder_exists()
            self.log_message.emit(f"Output folder ready: {os.path.basename(output_folder)}")
            self.log_manager.add_log_entry(f"Output folder: {output_folder}")
            return True
            
        except Exception as e:
            self.log_message.emit(f"Error preparing output folder: {str(e)}")
            self.log_manager.add_log_entry(f"Error preparing output folder: {str(e)}")
            return False
    
    def _convert_wav_files(self) -> bool:
        """WAV 파일들을 FLAC을 거쳐 HEX 데이터로 변환"""
        try:
            self.log_message.emit("\n" + "=" * LOG_WIDTH)
            self.log_message.emit("[ File Conversion ]")
            self.log_message.emit("=" * LOG_WIDTH)
            
            self.hex_data_list = []
            self.start_addresses = []
            
            # 시작 주소 계산
            base_address = int(self.hex_start_address, 16)
            current_address = self._calculate_initial_address(base_address)
            
            # 각 WAV 파일 처리
            for wav_file in self.wav_files:
                if not self._process_single_wav_file(wav_file, current_address):
                    return False
                    
                # 다음 파일을 위한 주소 계산
                if self.hex_data_list:
                    hex_data = self.hex_data_list[-1]
                    current_address += len(hex_data)
                    current_address = self._align_address(current_address)
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"Error during conversion: {str(e)}")
            self.log_manager.add_log_entry(f"Conversion error: {str(e)}")
            return False
    
    def _calculate_initial_address(self, base_address: int) -> int:
        """초기 주소 계산"""
        if self.sound_type == "Engine Sound":
            return base_address + AudioConstants.ENGINE_HEADER_SIZE
        else:  # Event Sound
            return base_address + AudioConstants.EVENT_HEADER_SIZE
    
    def _process_single_wav_file(self, wav_file: str, current_address: int) -> bool:
        """단일 WAV 파일 처리"""
        wav_file_path = os.path.join(self.input_folder, wav_file)
        
        try:
            # WAV → FLAC 변환
            flac_data = self.audio_processor.wav_to_flac(wav_file_path)
            
            # FLAC → HEX 데이터 변환
            hex_data = self.audio_processor.create_hex_data(flac_data, self.sound_type, wav_file)
            
            # 결과 저장
            self.hex_data_list.append(hex_data)
            self.start_addresses.append(current_address)
            
            # 로그 메시지
            self.log_message.emit(f"Converted successfully : {wav_file}")
            self.log_manager.add_log_entry(f"Converted: {wav_file}")
            
            return True
            
        except (AudioFileError, FlacConversionError) as e:
            self.log_message.emit(f"Conversion Failed : {wav_file} : {str(e)}")
            self.log_manager.add_log_entry(f"Failed: {wav_file} - {str(e)}")
            return False
        except Exception as e:
            self.log_message.emit(f"Unexpected error processing {wav_file}: {str(e)}")
            self.log_manager.add_log_entry(f"Unexpected error: {wav_file} - {str(e)}")
            return False
    
    def _align_address(self, address: int) -> int:
        """주소를 4바이트 경계로 정렬"""
        if address % AudioConstants.WORD_ALIGNMENT != 0:
            address += AudioConstants.WORD_ALIGNMENT - (address % AudioConstants.WORD_ALIGNMENT)
        return address
    
    def _log_file_info(self):
        """파일 정보 테이블 로그 출력"""
        try:
            self.log_message.emit("\n" + "-" * LOG_WIDTH)
            self.log_message.emit(f"{'File Name':<50} | {'Start Address':>13} | {'Data Length':>11}")
            self.log_message.emit("-" * LOG_WIDTH)
            
            for i, (wav_file, start_addr, hex_data) in enumerate(zip(self.wav_files, self.start_addresses, self.hex_data_list)):
                file_name = os.path.basename(wav_file)
                # 파일명이 너무 길면 자르고 "..." 추가
                if len(file_name) > 47:
                    file_name = file_name[:44] + "..."
                file_name_formatted = f"{file_name:<50}"
                start_address_formatted = f"0x{start_addr:08X}"
                data_length_formatted = f"0x{len(hex_data):08X}"
                self.log_message.emit(f"{file_name_formatted} | {start_address_formatted:>13} | {data_length_formatted:>11}")
            
            self.log_message.emit("-" * LOG_WIDTH)
            
        except Exception as e:
            self.log_message.emit(f"Error logging file info: {str(e)}")
    
    def _merge_and_save_files(self) -> bool:
        """HEX 데이터 병합 및 파일 저장"""
        try:
            self.log_message.emit("\n" + "=" * LOG_WIDTH)
            self.log_message.emit("[ File Generation ]")
            self.log_message.emit("=" * LOG_WIDTH)
            
            # 사운드 포지션 처리 (엔진 사운드만)
            sound_positions = self._get_sound_positions()
            
            # HEX 데이터 병합
            merged_hex = self.hex_merger.merge_hex_data_list(self.hex_data_list, sound_positions)
            
            # 파일 저장
            return self._save_output_files(merged_hex)
            
        except Exception as e:
            self.log_message.emit(f"Error during merge and save: {str(e)}")
            self.log_manager.add_log_entry(f"Merge/save error: {str(e)}")
            return False
    
    def _get_sound_positions(self) -> list:
        """사운드 포지션 가져오기 (엔진 사운드 전용)"""
        if self.sound_type == "Engine Sound":
            return [hex(addr)[2:].upper().zfill(8) for addr in self.start_addresses]
        return None
    
    def _save_output_files(self, merged_hex: IntelHex) -> bool:
        """출력 파일들 저장"""
        try:
            if self.sound_type == "Engine Sound":
                return self._save_engine_files(merged_hex)
            else:  # Event Sound
                return self._save_event_files(merged_hex)
                
        except Exception as e:
            self.log_message.emit(f"Error saving files: {str(e)}")
            self.log_manager.add_log_entry(f"File save error: {str(e)}")
            return False
    
    def _save_engine_files(self, merged_hex: IntelHex) -> bool:
        """엔진 사운드 파일들 저장"""
        try:
            # FLAC 파일들의 총 데이터 크기 계산
            total_flac_size = 0
            for temp_ih in self.hex_data_list:
                # FLAC 데이터 크기 계산 (헤더 4바이트 제외)
                flac_size = (temp_ih[0x0000] | (temp_ih[0x0001] << 8) | (temp_ih[0x0002] << 16) | (temp_ih[0x0003] << 24))
                total_flac_size += flac_size
            
            # BIN 파일 저장
            bin_filename = self.file_manager.save_bin_file(merged_hex)
            self.log_message.emit(f"Total data size: {total_flac_size:,} bytes")
            self.log_message.emit(f"Created BIN file: {bin_filename}")
            self.log_manager.add_log_entry(f"Created BIN: {bin_filename}")
            
            # 헤더 파일 저장
            header_filename = self.file_manager.save_header_file(merged_hex)
            self.log_message.emit(f"Created header file: {header_filename}")
            self.log_manager.add_log_entry(f"Created header: {header_filename}")
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"Error saving engine files: {str(e)}")
            return False
    
    def _save_event_files(self, merged_hex: IntelHex) -> bool:
        """이벤트 사운드 파일들 저장"""
        try:
            # HEX 파일 저장
            hex_filename = self.file_manager.save_hex_file(merged_hex)
            
            # HEX 파일 크기 출력 (먼저)
            hex_file_size = merged_hex.maxaddr() - merged_hex.minaddr() + 1
            self.log_message.emit(f"HEX file size: {hex_file_size:,} bytes ({hex_file_size/1024:.2f} KB)")
            self.log_manager.add_log_entry(f"HEX size: {hex_file_size} bytes")
            
            # 생성 파일명 출력 (나중)
            self.log_message.emit(f"Created HEX file: {hex_filename}")
            self.log_manager.add_log_entry(f"Created HEX: {hex_filename}")
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"Error saving event files: {str(e)}")
            return False
    
    def _show_engine_address_dialog(self):
        """엔진 사운드용 주소 설정 다이얼로그 표시"""
        try:
            # 기본 사운드 포지션 (10개 슬롯, 모두 FFFFFFFF로 초기화)
            sound_positions = ["FFFFFFFF"] * 10
            self.show_info_dialog.emit(self.wav_files, self.start_addresses, sound_positions)
        except Exception as e:
            self.log_message.emit(f"Error showing address dialog: {str(e)}")
            self.finished.emit()
    
    def complete_engine_processing(self, updated_positions):
        """엔진 사운드 처리 완료 (AddressSettingDialog에서 호출됨)"""
        try:
            self.log_message.emit("\n" + "=" * LOG_WIDTH)
            self.log_message.emit("[ File Generation ]")
            self.log_message.emit("=" * LOG_WIDTH)
            
            # 업데이트된 포지션으로 병합
            merged_hex = self.hex_merger.merge_hex_data_list(self.hex_data_list, updated_positions)
            
            # 파일 저장
            if self._save_engine_files(merged_hex):
                self._finalize_processing()
            else:
                self.finished.emit()
                
        except Exception as e:
            self.log_message.emit(f"Error completing engine processing: {str(e)}")
            self.finished.emit()

    def _finalize_processing(self):
        """처리 완료 및 정리"""
        try:
            # 로그 자동 저장
            log_filename, _ = self.log_manager.save_log_to_csv(manual_save=False)
            self.log_message.emit(f"Log saved: {log_filename}")
            
            # 완료 메시지
            self.log_message.emit("\nProcessing completed successfully")
            
            # 자동 로그 저장 시그널
            self.save_log.emit()
            
            # 스레드 완료
            self.finished.emit()
            
        except Exception as e:
            self.log_message.emit(f"Error during finalization: {str(e)}")
            self.finished.emit()

class AddressSettingDialog(QDialog):
    """주소 설정 다이얼로그 (기존 기능 유지)"""
    
    def __init__(self, wav_files, start_addresses, sound_positions, parent=None):
        super().__init__(parent)
        self.wav_files = wav_files
        self.start_addresses = start_addresses
        self.sound_positions = sound_positions
        self.setWindowTitle("Engine Sound Address Settings")
        self.setModal(True)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 구성"""
        # 창 크기를 WAV 파일 수에 따라 동적으로 조정
        base_height = 100
        row_height = 40
        table_height = len(self.wav_files) * row_height + 30  # 헤더 높이 포함
        # 테이블 너비에 맞춰 창 크기 조정 (여백 포함)
        dialog_width = UIConstants.WAV_FILE_COLUMN_WIDTH + UIConstants.ADDRESS_COLUMN_WIDTH + 50
        self.setGeometry(150, 150, dialog_width, base_height + table_height)
        
        layout = QVBoxLayout()
        
        # 설명 레이블
        desc_label = QLabel("Set the starting address for each sound file:")
        layout.addWidget(desc_label)
        
        # 테이블 생성
        table = QTableWidget()
        table.setColumnCount(2)
        table.setRowCount(len(self.wav_files))
        table.setHorizontalHeaderLabels(["WAV File", "Start Address"])
        
        # 컬럼 너비 설정
        table.setColumnWidth(0, UIConstants.WAV_FILE_COLUMN_WIDTH)
        table.setColumnWidth(1, UIConstants.ADDRESS_COLUMN_WIDTH)
        
        # 테이블 크기 정책 설정 - 수평 스크롤바 제거
        table.horizontalHeader().setStretchLastSection(False)
        table.setHorizontalScrollBarPolicy(1)  # ScrollBarAlwaysOff
        
        # 테이블 높이 설정
        table.setFixedHeight(table_height)
        # 테이블 너비를 컬럼 너비에 맞춰 고정
        table.setFixedWidth(UIConstants.WAV_FILE_COLUMN_WIDTH + UIConstants.ADDRESS_COLUMN_WIDTH + UIConstants.TABLE_MARGIN)
        
        self.start_address_items = []  # Start Address 아이템 저장
        
        # 각 행에 데이터 채우기
        for i, (wav_file, start_addr) in enumerate(zip(self.wav_files, self.start_addresses)):
            # WAV 파일명
            file_item = QTableWidgetItem(wav_file)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)  # 편집 불가
            table.setItem(i, 0, file_item)
            
            # 시작 주소 (편집 가능)
            addr_item = QTableWidgetItem(hex(start_addr)[2:].upper().zfill(8))
            table.setItem(i, 1, addr_item)
            self.start_address_items.append(addr_item)
        
        layout.addWidget(table)
        
        # Engine Sound Positions 정보
        if self.sound_positions:
            positions_group = QGroupBox("Engine Sound Positions")
            positions_layout = QGridLayout()
            
            position_labels = [
                "Sound F1 position:", "Sound F2 position:", "Sound F3 position:",
                "Sound S1 position:", "Sound S2 position:", "Sound S3 position:",
                "Sound C1 position:", "Sound C2 position:",
                "Sound R1 position:", "Sound R2 position:"
            ]
            
            self.position_edits = []  # 수정된 포지션 값을 저장할 리스트
            for i, (label_text, position) in enumerate(zip(position_labels, self.sound_positions)):
                label = QLabel(label_text)
                edit = QLineEdit(position)
                edit.setMaxLength(8)  # 8자리 16진수
                edit.setValidator(QRegExpValidator(QRegExp("[0-9A-Fa-f]{8}")))  # 16진수만 입력 가능
                self.position_edits.append(edit)
                positions_layout.addWidget(label, i, 0)
                positions_layout.addWidget(edit, i, 1)
                
            positions_group.setLayout(positions_layout)
            layout.addWidget(positions_group)
        
        # Apply 버튼
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.accept)
        layout.addWidget(apply_button)
        
        self.setLayout(layout)
    
    def get_sound_positions(self):
        """사운드 포지션 가져오기"""
        return [edit.text().upper() for edit in self.position_edits] if hasattr(self, 'position_edits') else []
    
    def accept(self):
        """확인 버튼 클릭 시"""
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
            
            # 매치되지 않은 position이 있는 경우 에러 메시지 표시
            if unmatched_positions:
                error_msg = "Error: The following positions have unmatched addresses:\n"
                for pos in unmatched_positions:
                    error_msg += f"- {pos}\n"
                error_msg += "\nPlease check the addresses and try again."
                QMessageBox.critical(self, "Error", error_msg)
                return  # 처리를 중단하고 다이얼로그를 닫지 않음
        
        self.sound_positions = self.get_sound_positions()
        super().accept()
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        event.accept() 
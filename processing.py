"""
=========================================================================================
📌 File:         processing.py
📌 Description:  Processing thread and address dialog for AVAS40 WavConverter
📌 Author:       Geunwoo Lee
📌 Date:         2025-01-15
📌 Version:      1.00
=========================================================================================
📌 Main Features:
    - ProcessingThread: Background audio processing thread
    - AddressSettingDialog: Engine sound address setting dialog
    - Manages full process: WAV → FLAC → HEX → merge → file save
    - Branches flow by sound type (Engine vs Event)
    
📌 ProcessingThread Key Methods:
    - run(): Main processing logic (WAV validation → conversion → merge → save)
    - _convert_wav_files(): Convert WAV files to FLAC and then to HEX
    - _merge_and_save_files(): Merge HEX data and save files
    - _show_engine_address_dialog(): Show engine address dialog
    - complete_engine_processing(): Complete engine sound processing
    - _finalize_processing(): Finalize and cleanup
    
📌 AddressSettingDialog Key Features:
    - Table of start addresses for each WAV file
    - 10 engine sound positions (F1-F3, S1-S3, C1-C2, R1-R2)
    - Address validation and matching
    - Hexadecimal input validation
    
📌 Processing Flow:
    Engine Sound: WAV→Dialog→User setting→Merge/Save
    Event Sound: WAV→File info log→Merge/Save
    
📌 Dependencies:
    - Standard library: os
    - PyQt5: QDialog, QThread, QTableWidget, etc.
    - External library: intelhex
    - Local modules: utils, audio_processor, file_manager
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
    """Audio file processing thread (refactored version)"""
    
    finished = pyqtSignal()
    log_message = pyqtSignal(str)
    save_log = pyqtSignal()
    show_info_dialog = pyqtSignal(list, list, list)
    no_wav_files = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_parameters()
        
    def _init_parameters(self):
        """Initialize parameters"""
        self.input_folder = ""
        self.compression_level = AudioConstants.DEFAULT_COMPRESSION
        self.block_size = AudioConstants.DEFAULT_BLOCK_SIZE
        self.sound_type = "Engine Sound"
        self.hex_start_address = AudioConstants.DEFAULT_START_ADDRESS
        self.hex_file_size_kb = "864.00"
        
        # Processing result data
        self.hex_data_list = []
        self.wav_files = []
        self.start_addresses = []
        
        # Processing objects
        self.audio_processor = None
        self.hex_merger = None
        self.file_manager = None
        self.log_manager = None
        
    def set_parameters(self, input_folder, compression_level, block_size, sound_type, hex_start_address, hex_file_size_kb):
        """Set processing parameters"""
        self.input_folder = input_folder
        self.compression_level = compression_level
        self.block_size = block_size
        self.sound_type = sound_type
        self.hex_start_address = hex_start_address
        self.hex_file_size_kb = hex_file_size_kb
        
        # Initialize processing objects
        self._init_processors()
        
    def _init_processors(self):
        """Initialize processing objects"""
        self.audio_processor = AudioProcessor(self.compression_level, self.block_size)
        self.hex_merger = HexMerger(self.sound_type, self.hex_start_address)
        self.file_manager = FileManager(self.sound_type)
        self.log_manager = LogManager(self.sound_type)
        
    def run(self):
        """Main processing logic"""
        try:
            self.log_message.emit("Starting processing")
            self.log_manager.add_log_entry("Processing started")
            
            # 1. Find and validate WAV files
            if not self._find_and_validate_wav_files():
                return
            
            # 2. Prepare output folder
            if not self._prepare_output_folder():
                return
            
            # 3. Convert WAV → FLAC → HEX
            if not self._convert_wav_files():
                return
            
            # 3.5. Output file info log (Event Sound only)
            if self.sound_type == "Event Sound":
                self._log_file_info()
            
            # 4. Branch by sound type
            if self.sound_type == "Engine Sound":
                # Engine sound: show AddressSettingDialog, then continue
                self._show_engine_address_dialog()
            else:
                # Event sound: merge/save immediately
                if not self._merge_and_save_files():
                    return
                self._finalize_processing()
            
        except Exception as e:
            error_msg = f"Error in processing thread: {str(e)}"
            self.log_message.emit(error_msg)
            self.log_manager.add_log_entry(f"Error: {str(e)}")
            self.finished.emit()  # Emit finished signal even on error
            
    def _find_and_validate_wav_files(self) -> bool:
        """Find and validate WAV files"""
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
        """Prepare output folder"""
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
        """Convert WAV files to FLAC and then to HEX data"""
        try:
            self.log_message.emit("\n" + "=" * LOG_WIDTH)
            self.log_message.emit("[ File Conversion ]")
            self.log_message.emit("=" * LOG_WIDTH)
            
            self.hex_data_list = []
            self.start_addresses = []
            
            # Calculate initial address
            base_address = int(self.hex_start_address, 16)
            current_address = self._calculate_initial_address(base_address)
            
            # Process each WAV file
            for wav_file in self.wav_files:
                if not self._process_single_wav_file(wav_file, current_address):
                    return False
                    
                # Calculate address for next file
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
        """Calculate initial address"""
        if self.sound_type == "Engine Sound":
            return base_address + AudioConstants.ENGINE_HEADER_SIZE
        else:  # Event Sound
            return base_address + AudioConstants.EVENT_HEADER_SIZE
    
    def _process_single_wav_file(self, wav_file: str, current_address: int) -> bool:
        """Process a single WAV file"""
        wav_file_path = os.path.join(self.input_folder, wav_file)
        
        try:
            # WAV → FLAC conversion
            flac_data = self.audio_processor.wav_to_flac(wav_file_path)
            
            # FLAC → HEX data conversion
            hex_data = self.audio_processor.create_hex_data(flac_data, self.sound_type, wav_file)
            
            # Save result
            self.hex_data_list.append(hex_data)
            self.start_addresses.append(current_address)
            
            # Log message
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
        """Align address to 4-byte boundary"""
        if address % AudioConstants.WORD_ALIGNMENT != 0:
            address += AudioConstants.WORD_ALIGNMENT - (address % AudioConstants.WORD_ALIGNMENT)
        return address
    
    def _log_file_info(self):
        """Output file info table to log"""
        try:
            self.log_message.emit("\n" + "-" * LOG_WIDTH)
            self.log_message.emit(f"{'File Name':<50} | {'Start Address':>13} | {'Data Length':>11}")
            self.log_message.emit("-" * LOG_WIDTH)
            
            for i, (wav_file, start_addr, hex_data) in enumerate(zip(self.wav_files, self.start_addresses, self.hex_data_list)):
                file_name = os.path.basename(wav_file)
                # If file name is too long, truncate and add "..."
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
        """Merge HEX data and save files"""
        try:
            self.log_message.emit("\n" + "=" * LOG_WIDTH)
            self.log_message.emit("[ File Generation ]")
            self.log_message.emit("=" * LOG_WIDTH)
            
            # Process sound positions (engine sound only)
            sound_positions = self._get_sound_positions()
            
            # Merge HEX data
            merged_hex = self.hex_merger.merge_hex_data_list(self.hex_data_list, sound_positions)
            
            # Save files
            return self._save_output_files(merged_hex)
            
        except Exception as e:
            self.log_message.emit(f"Error during merge and save: {str(e)}")
            self.log_manager.add_log_entry(f"Merge/save error: {str(e)}")
            return False
    
    def _get_sound_positions(self) -> list:
        """Get sound positions (engine sound only)"""
        if self.sound_type == "Engine Sound":
            return [hex(addr)[2:].upper().zfill(8) for addr in self.start_addresses]
        return None
    
    def _save_output_files(self, merged_hex: IntelHex) -> bool:
        """Save output files"""
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
        """Save engine sound files"""
        try:
            # Calculate total FLAC data size
            total_flac_size = 0
            for temp_ih in self.hex_data_list:
                # Calculate FLAC data size (excluding 4-byte header)
                flac_size = (temp_ih[0x0000] | (temp_ih[0x0001] << 8) | (temp_ih[0x0002] << 16) | (temp_ih[0x0003] << 24))
                total_flac_size += flac_size
            
            # Save BIN file
            bin_filename = self.file_manager.save_bin_file(merged_hex)
            self.log_message.emit(f"Total data size: {total_flac_size:,} bytes")
            self.log_message.emit(f"Created BIN file: {bin_filename}")
            self.log_manager.add_log_entry(f"Created BIN: {bin_filename}")
            
            # Save header file
            header_filename = self.file_manager.save_header_file(merged_hex)
            self.log_message.emit(f"Created header file: {header_filename}")
            self.log_manager.add_log_entry(f"Created header: {header_filename}")
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"Error saving engine files: {str(e)}")
            return False
    
    def _save_event_files(self, merged_hex: IntelHex) -> bool:
        """Save event sound files"""
        try:
            # Save HEX file
            hex_filename = self.file_manager.save_hex_file(merged_hex)
            
            # Output HEX file size (first)
            hex_file_size = merged_hex.maxaddr() - merged_hex.minaddr() + 1
            self.log_message.emit(f"HEX file size: {hex_file_size:,} bytes ({hex_file_size/1024:.2f} KB)")
            self.log_manager.add_log_entry(f"HEX size: {hex_file_size} bytes")
            
            # Output created file name (after)
            self.log_message.emit(f"Created HEX file: {hex_filename}")
            self.log_manager.add_log_entry(f"Created HEX: {hex_filename}")
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"Error saving event files: {str(e)}")
            return False
    
    def _show_engine_address_dialog(self):
        """Show address setting dialog for engine sound"""
        try:
            # Default sound positions (10 slots, all FFFFFFFF)
            sound_positions = ["FFFFFFFF"] * 10
            self.show_info_dialog.emit(self.wav_files, self.start_addresses, sound_positions)
        except Exception as e:
            self.log_message.emit(f"Error showing address dialog: {str(e)}")
            self.finished.emit()
    
    def complete_engine_processing(self, updated_positions):
        """Complete engine sound processing (called from AddressSettingDialog)"""
        try:
            self.log_message.emit("\n" + "=" * LOG_WIDTH)
            self.log_message.emit("[ File Generation ]")
            self.log_message.emit("=" * LOG_WIDTH)
            
            # Merge with updated positions
            merged_hex = self.hex_merger.merge_hex_data_list(self.hex_data_list, updated_positions)
            
            # Save files
            if self._save_engine_files(merged_hex):
                self._finalize_processing()
            else:
                self.finished.emit()
                
        except Exception as e:
            self.log_message.emit(f"Error completing engine processing: {str(e)}")
            self.finished.emit()

    def _finalize_processing(self):
        """Finalize and cleanup"""
        try:
            # Auto-save log
            log_filename, _ = self.log_manager.save_log_to_csv(manual_save=False)
            self.log_message.emit(f"Log saved: {log_filename}")
            
            # Completion message
            self.log_message.emit("\nProcessing completed successfully")
            
            # Auto-save log signal
            self.save_log.emit()
            
            # Thread finished
            self.finished.emit()
            
        except Exception as e:
            self.log_message.emit(f"Error during finalization: {str(e)}")
            self.finished.emit()

class AddressSettingDialog(QDialog):
    """Address setting dialog (legacy feature maintained)"""
    
    def __init__(self, wav_files, start_addresses, sound_positions, parent=None):
        super().__init__(parent)
        self.wav_files = wav_files
        self.start_addresses = start_addresses
        self.sound_positions = sound_positions
        self.setWindowTitle("Engine Sound Address Settings")
        self.setModal(True)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """UI setup"""
        # Dynamically adjust window size based on number of WAV files
        base_height = 100
        row_height = 40
        table_height = len(self.wav_files) * row_height + 30  # Include header height
        # Adjust window width to fit table (including margin)
        dialog_width = UIConstants.WAV_FILE_COLUMN_WIDTH + UIConstants.ADDRESS_COLUMN_WIDTH + 50
        self.setGeometry(150, 150, dialog_width, base_height + table_height)
        
        layout = QVBoxLayout()
        
        # Description label
        desc_label = QLabel("Set the starting address for each sound file:")
        layout.addWidget(desc_label)
        
        # Create table
        table = QTableWidget()
        table.setColumnCount(2)
        table.setRowCount(len(self.wav_files))
        table.setHorizontalHeaderLabels(["WAV File", "Start Address"])
        
        # Set column widths
        table.setColumnWidth(0, UIConstants.WAV_FILE_COLUMN_WIDTH)
        table.setColumnWidth(1, UIConstants.ADDRESS_COLUMN_WIDTH)
        
        # Set table size policy - remove horizontal scrollbar
        table.horizontalHeader().setStretchLastSection(False)
        table.setHorizontalScrollBarPolicy(1)  # ScrollBarAlwaysOff
        
        # Set table height
        table.setFixedHeight(table_height)
        # Fix table width to column widths
        table.setFixedWidth(UIConstants.WAV_FILE_COLUMN_WIDTH + UIConstants.ADDRESS_COLUMN_WIDTH + UIConstants.TABLE_MARGIN)
        
        self.start_address_items = []  # Store Start Address items
        
        # Fill data for each row
        for i, (wav_file, start_addr) in enumerate(zip(self.wav_files, self.start_addresses)):
            # WAV file name
            file_item = QTableWidgetItem(wav_file)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)  # Not editable
            table.setItem(i, 0, file_item)
            
            # Start address (editable)
            addr_item = QTableWidgetItem(hex(start_addr)[2:].upper().zfill(8))
            table.setItem(i, 1, addr_item)
            self.start_address_items.append(addr_item)
        
        layout.addWidget(table)
        
        # Engine Sound Positions info
        if self.sound_positions:
            positions_group = QGroupBox("Engine Sound Positions")
            positions_layout = QGridLayout()
            
            position_labels = [
                "Sound F1 position:", "Sound F2 position:", "Sound F3 position:",
                "Sound S1 position:", "Sound S2 position:", "Sound S3 position:",
                "Sound C1 position:", "Sound C2 position:",
                "Sound R1 position:", "Sound R2 position:"
            ]
            
            self.position_edits = []  # List to store edited positions
            for i, (label_text, position) in enumerate(zip(position_labels, self.sound_positions)):
                label = QLabel(label_text)
                edit = QLineEdit(position)
                edit.setMaxLength(8)  # 8-digit hex
                edit.setValidator(QRegExpValidator(QRegExp("[0-9A-Fa-f]{8}")))  # Only hex allowed
                self.position_edits.append(edit)
                positions_layout.addWidget(label, i, 0)
                positions_layout.addWidget(edit, i, 1)
                
            positions_group.setLayout(positions_layout)
            layout.addWidget(positions_group)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.accept)
        layout.addWidget(apply_button)
        
        self.setLayout(layout)
    
    def get_sound_positions(self):
        """Get sound positions"""
        return [edit.text().upper() for edit in self.position_edits] if hasattr(self, 'position_edits') else []
    
    def accept(self):
        """On Apply button click"""
        # Output Engine Sound Position info to log
        if hasattr(self, 'position_edits'):
            # List for address matching check
            unmatched_positions = []
            
            # Output position labels and values
            position_labels = [
                "Sound F1 ", "Sound F2 ", "Sound F3 ",
                "Sound S1 ", "Sound S2 ", "Sound S3 ",
                "Sound C1 ", "Sound C2 ",
                "Sound R1 ", "Sound R2 "
            ]
            
            for i, (label, edit) in enumerate(zip(position_labels, self.position_edits)):
                position_value = edit.text().upper()
                if position_value != "FFFFFFFF":
                    # Convert input address to hex
                    try:
                        position_addr = int(position_value, 16)
                        # Find matching WAV file for this address
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
            
            # If there are unmatched positions, show error message
            if unmatched_positions:
                error_msg = "Error: The following positions have unmatched addresses:\n"
                for pos in unmatched_positions:
                    error_msg += f"- {pos}\n"
                error_msg += "\nPlease check the addresses and try again."
                QMessageBox.critical(self, "Error", error_msg)
                return  # Do not close dialog, stop processing
        
        self.sound_positions = self.get_sound_positions()
        super().accept()
    
    def closeEvent(self, event):
        """On dialog close event"""
        event.accept() 
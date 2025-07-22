"""
=========================================================================================
📌 File:         audio_processor.py
📌 Description:  Audio processing module for AVAS40 WavConverter
📌 Author:       Geunwoo Lee
📌 Date:         2025-01-15
📌 Version:      1.00
=========================================================================================
📌 Main Features:
    - AudioProcessor: Converts WAV to FLAC and generates HEX data
    - HexMerger: Merges multiple HEX data and generates headers
    - WAV downsampling: 48kHz → 24kHz conversion
    - In-memory FLAC conversion (no file creation)
    
📌 AudioProcessor Key Methods:
    - wav_to_flac(): Convert WAV to FLAC (in-memory)
    - create_hex_data(): Convert FLAC data to IntelHex object
    - _downsample_and_convert_to_flac(): Downsample 48kHz and convert to FLAC
    - _convert_file_to_flac(): Directly convert 24kHz WAV to FLAC
    
📌 HexMerger Key Methods:
    - merge_hex_data_list(): Merge list of HEX data
    - _add_engine_header(): Add engine sound header (Magic Key + Positions)
    - _add_event_header(): Add event sound header
    - _add_padding(): 4-byte alignment padding
    
📌 Features:
    - No FLAC file is created on disk (all in-memory)
    - Uses stdout/stdin for pipeline conversion
    - Supports 864KB fixed size padding for engine sound
    
📌 Dependencies:
    - Standard library: os, subprocess, wave, io
    - External library: intelhex
    - Local module: utils (constants, exception classes)
    - External executable: flac.exe
=========================================================================================
"""

import os
import subprocess
import wave
import io
from intelhex import IntelHex
from utils import AudioConstants, FlacConversionError, AudioFileError, get_exe_directory

class AudioProcessor:
    """Audio file processing class"""
    
    def __init__(self, compression_level=None, block_size=None):
        self.compression_level = compression_level or AudioConstants.DEFAULT_COMPRESSION
        self.block_size = block_size or AudioConstants.DEFAULT_BLOCK_SIZE
    
    def wav_to_flac(self, wav_file_path: str) -> bytes:
        """Convert WAV to FLAC and return bytes (no file creation)"""
        if not os.path.exists(wav_file_path):
            raise AudioFileError(f"WAV file not found: {wav_file_path}")
        
        # Normalize path
        wav_file_path = os.path.normpath(wav_file_path)
        
        # Check sample rate
        with wave.open(wav_file_path, 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            n_frames = wav_file.getnframes()
            frames = wav_file.readframes(n_frames)
        
        flac_exe = os.path.join(get_exe_directory(), "flac.exe")
        if not os.path.exists(flac_exe):
            raise FlacConversionError("flac.exe not found in application directory")
        
        if sample_rate == 48000:
            # Downsample 48kHz to 24kHz and convert to FLAC (in-memory)
            return self._downsample_and_convert_to_flac(frames, sample_width, n_channels, flac_exe)
        elif sample_rate == 24000:
            # Directly convert 24kHz WAV to FLAC
            return self._convert_file_to_flac(wav_file_path, flac_exe)
        else:
            raise AudioFileError(f"Unsupported sample rate: {sample_rate}Hz")
    
    def _downsample_and_convert_to_flac(self, frames: bytes, sample_width: int, n_channels: int, flac_exe: str) -> bytes:
        """Downsample 48kHz to 24kHz and convert to FLAC (in-memory, no file creation)"""
        try:
            # 2:1 downsampling
            frame_size = sample_width * n_channels
            num_frames = len(frames) // frame_size
            
            downsampled_frames = bytearray()
            for i in range(0, num_frames, 2):
                start_pos = i * frame_size
                end_pos = start_pos + frame_size
                downsampled_frames.extend(frames[start_pos:end_pos])
            
            # Create WAV in memory
            temp_wav_data = io.BytesIO()
            with wave.open(temp_wav_data, 'wb') as out_wav:
                out_wav.setnchannels(n_channels)
                out_wav.setsampwidth(sample_width)
                out_wav.setframerate(24000)
                out_wav.writeframes(downsampled_frames)
            
            # FLAC conversion (stdin input, stdout output)
            flac_command = [
                f'"{flac_exe}"',
                "--no-padding",
                f"-{self.compression_level}",
                f"--blocksize={self.block_size}",
                "-",  # stdin input
                "-c"  # stdout output
            ]
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                " ".join(flac_command), 
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                startupinfo=startupinfo
            )
            flac_data, stderr = process.communicate(input=temp_wav_data.getvalue())
            
            if process.returncode != 0:
                raise FlacConversionError(f"FLAC conversion failed: {stderr.decode()}")
            
            return flac_data
            
        except Exception as e:
            raise FlacConversionError(f"Error during downsample and FLAC conversion: {str(e)}")
    
    def _convert_file_to_flac(self, wav_file_path: str, flac_exe: str) -> bytes:
        """Directly convert 24kHz WAV to FLAC (stdout, no file creation)"""
        try:
            flac_command = [
                f'"{flac_exe}"',
                "--no-padding",
                f"-{self.compression_level}",
                f"--blocksize={self.block_size}",
                f'"{wav_file_path}"',
                "-c"  # stdout output
            ]
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                " ".join(flac_command), 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                startupinfo=startupinfo,
                check=True
            )
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            raise FlacConversionError(f"FLAC conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
    
    def create_hex_data(self, flac_data: bytes, sound_type: str, wav_filename: str = "") -> IntelHex:
        """Create IntelHex object from FLAC data"""
        if not flac_data:
            raise AudioFileError("Empty FLAC data provided")
        
        ih = IntelHex()
        flac_size = len(flac_data)
        
        # Store FLAC size in 4 bytes
        ih[AudioConstants.FLAC_SIZE_OFFSET] = flac_size & 0xFF
        ih[AudioConstants.FLAC_SIZE_OFFSET + 1] = (flac_size >> 8) & 0xFF
        ih[AudioConstants.FLAC_SIZE_OFFSET + 2] = (flac_size >> 16) & 0xFF
        ih[AudioConstants.FLAC_SIZE_OFFSET + 3] = (flac_size >> 24) & 0xFF
        
        if sound_type == "Engine Sound":
            # Engine sound: include filename
            self._add_engine_data(ih, flac_data, wav_filename)
        else:
            # Event sound: FLAC data only
            self._add_event_data(ih, flac_data)
        
        return ih
    
    def _add_engine_data(self, ih: IntelHex, flac_data: bytes, wav_filename: str):
        """Add engine sound data (filename + FLAC data)"""
        # Store filename in 80-byte buffer
        filename_bytes = wav_filename.ljust(AudioConstants.FILENAME_BUFFER_SIZE, '\x00').encode('utf-8')
        
        for i, byte in enumerate(filename_bytes):
            ih[AudioConstants.ENGINE_FILENAME_OFFSET + i] = byte
        
        # Store FLAC data
        for i, byte in enumerate(flac_data):
            ih[AudioConstants.ENGINE_FLAC_DATA_OFFSET + i] = byte
    
    def _add_event_data(self, ih: IntelHex, flac_data: bytes):
        """Add event sound data (FLAC data only)"""
        for i, byte in enumerate(flac_data):
            ih[AudioConstants.EVENT_FLAC_DATA_OFFSET + i] = byte

class HexMerger:
    """HEX data merging class"""
    
    def __init__(self, sound_type: str, start_address: str):
        self.sound_type = sound_type
        self.start_address = int(start_address, 16)
    
    def merge_hex_data_list(self, hex_data_list: list, sound_positions: list = None) -> IntelHex:
        """Merge list of HEX data"""
        if not hex_data_list:
            raise AudioFileError("No HEX data to merge")
        
        ih = IntelHex()
        current_address = self.start_address
        
        if self.sound_type == "Event Sound":
            current_address = self._add_event_header(ih, current_address)
            current_address = self._merge_event_data(ih, hex_data_list, current_address)
        else:  # Engine Sound
            current_address = self._add_engine_header(ih, current_address, sound_positions)
            current_address = self._merge_engine_data(ih, hex_data_list, current_address)
        
        return ih
    
    def _add_event_header(self, ih: IntelHex, current_address: int) -> int:
        """Add event sound header"""
        for _ in range(AudioConstants.EVENT_HEADER_SIZE):
            ih[current_address] = 0xFF
            current_address += 1
        return current_address
    
    def _add_engine_header(self, ih: IntelHex, current_address: int, sound_positions: list) -> int:
        """Add engine sound header (Magic Key + Sound Positions)"""
        # Add Magic Key
        magic_key = AudioConstants.MAGIC_KEY
        ih[current_address] = magic_key & 0xFF
        ih[current_address + 1] = (magic_key >> 8) & 0xFF
        ih[current_address + 2] = (magic_key >> 16) & 0xFF
        ih[current_address + 3] = (magic_key >> 24) & 0xFF
        current_address += 4
        
        # Add Sound Positions
        if sound_positions:
            for position in sound_positions:
                pos_value = int(position, 16)
                ih[current_address] = pos_value & 0xFF
                ih[current_address + 1] = (pos_value >> 8) & 0xFF
                ih[current_address + 2] = (pos_value >> 16) & 0xFF
                ih[current_address + 3] = (pos_value >> 24) & 0xFF
                current_address += 4
        
        return current_address
    
    def _merge_event_data(self, ih: IntelHex, hex_data_list: list, current_address: int) -> int:
        """Merge event data"""
        for temp_ih in hex_data_list:
            # Copy data
            for address in range(temp_ih.minaddr(), temp_ih.maxaddr() + 1):
                ih[current_address] = temp_ih[address]
                current_address += 1
            
            # 4-byte alignment padding
            current_address = self._add_padding(ih, current_address)
        
        return current_address
    
    def _merge_engine_data(self, ih: IntelHex, hex_data_list: list, current_address: int) -> int:
        """Merge engine data"""
        start_address = self.start_address
        
        for temp_ih in hex_data_list:
            # Copy data
            for address in range(temp_ih.minaddr(), temp_ih.maxaddr() + 1):
                ih[current_address] = temp_ih[address]
                current_address += 1
            
            # 4-byte alignment padding
            current_address = self._add_padding(ih, current_address)
        
        # For engine sound, pad to fixed size (864KB)
        hex_file_size_bytes = int(864.0 * 1024)  # 864KB
        target_end_address = start_address + hex_file_size_bytes
        
        while current_address < target_end_address:
            ih[current_address] = 0xFF
            current_address += 1
        
        return current_address
    
    def _add_padding(self, ih: IntelHex, current_address: int) -> int:
        """Add padding for 4-byte alignment"""
        padding = current_address % AudioConstants.WORD_ALIGNMENT
        if padding != 0:
            padding_to_add = AudioConstants.WORD_ALIGNMENT - padding
            for _ in range(padding_to_add):
                ih[current_address] = 0xFF
                current_address += 1
        return current_address
    
    def get_hex_file_size(self) -> int:
        """Calculate merged HEX file size"""
        return self.current_size if hasattr(self, 'current_size') else 0 
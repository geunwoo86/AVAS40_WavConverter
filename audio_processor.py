"""
=========================================================================================
📌 파일명:      audio_processor.py
📌 설명:        AVAS40 WavConverter 오디오 처리 전용 모듈
📌 작성자:      Geunwoo Lee
📌 작성일:      2025-01-15
📌 버전:        1.00
=========================================================================================
"""

import os
import subprocess
import wave
import io
from intelhex import IntelHex
from utils import AudioConstants, FlacConversionError, AudioFileError, get_exe_directory

class AudioProcessor:
    """오디오 파일 처리 전용 클래스"""
    
    def __init__(self, compression_level=None, block_size=None):
        self.compression_level = compression_level or AudioConstants.DEFAULT_COMPRESSION
        self.block_size = block_size or AudioConstants.DEFAULT_BLOCK_SIZE
    
    def wav_to_flac(self, wav_file_path: str) -> bytes:
        """WAV 파일을 FLAC으로 변환하고 바이트 데이터 반환 (파일 생성하지 않음)"""
        if not os.path.exists(wav_file_path):
            raise AudioFileError(f"WAV file not found: {wav_file_path}")
        
        # 경로 정규화
        wav_file_path = os.path.normpath(wav_file_path)
        
        # WAV 파일의 샘플링 레이트 확인
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
            # 48kHz -> 24kHz 다운샘플링 + FLAC 변환 (메모리에서만 처리)
            return self._downsample_and_convert_to_flac(frames, sample_width, n_channels, flac_exe)
        elif sample_rate == 24000:
            # 24kHz면 원본 파일을 직접 FLAC 변환
            return self._convert_file_to_flac(wav_file_path, flac_exe)
        else:
            raise AudioFileError(f"Unsupported sample rate: {sample_rate}Hz")
    
    def _downsample_and_convert_to_flac(self, frames: bytes, sample_width: int, n_channels: int, flac_exe: str) -> bytes:
        """48kHz 다운샘플링 + FLAC 변환 (메모리에서만 처리, 파일 생성 안함)"""
        try:
            # 2:1 다운샘플링 수행
            frame_size = sample_width * n_channels
            num_frames = len(frames) // frame_size
            
            downsampled_frames = bytearray()
            for i in range(0, num_frames, 2):
                start_pos = i * frame_size
                end_pos = start_pos + frame_size
                downsampled_frames.extend(frames[start_pos:end_pos])
            
            # 다운샘플링된 데이터를 WAV 형태로 메모리에서 구성
            temp_wav_data = io.BytesIO()
            with wave.open(temp_wav_data, 'wb') as out_wav:
                out_wav.setnchannels(n_channels)
                out_wav.setsampwidth(sample_width)
                out_wav.setframerate(24000)
                out_wav.writeframes(downsampled_frames)
            
            # FLAC 변환 (stdin에서 입력, stdout으로 출력)
            flac_command = [
                f'"{flac_exe}"',
                "--no-padding",
                f"-{self.compression_level}",
                f"--blocksize={self.block_size}",
                "-",  # stdin에서 입력 받음
                "-c"  # stdout으로 출력
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
        """24kHz WAV 파일을 직접 FLAC으로 변환 (stdout 사용, 파일 생성 안함)"""
        try:
            flac_command = [
                f'"{flac_exe}"',
                "--no-padding",
                f"-{self.compression_level}",
                f"--blocksize={self.block_size}",
                f'"{wav_file_path}"',
                "-c"  # stdout으로 출력
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
        """FLAC 데이터로부터 IntelHex 객체 생성"""
        if not flac_data:
            raise AudioFileError("Empty FLAC data provided")
        
        ih = IntelHex()
        flac_size = len(flac_data)
        
        # FLAC 크기를 4바이트로 저장
        ih[AudioConstants.FLAC_SIZE_OFFSET] = flac_size & 0xFF
        ih[AudioConstants.FLAC_SIZE_OFFSET + 1] = (flac_size >> 8) & 0xFF
        ih[AudioConstants.FLAC_SIZE_OFFSET + 2] = (flac_size >> 16) & 0xFF
        ih[AudioConstants.FLAC_SIZE_OFFSET + 3] = (flac_size >> 24) & 0xFF
        
        if sound_type == "Engine Sound":
            # 엔진 사운드: 파일명 포함
            self._add_engine_data(ih, flac_data, wav_filename)
        else:
            # 이벤트 사운드: FLAC 데이터만
            self._add_event_data(ih, flac_data)
        
        return ih
    
    def _add_engine_data(self, ih: IntelHex, flac_data: bytes, wav_filename: str):
        """엔진 사운드 데이터 추가 (파일명 + FLAC 데이터)"""
        # 파일명을 80바이트 버퍼에 저장
        filename_bytes = wav_filename.ljust(AudioConstants.FILENAME_BUFFER_SIZE, '\x00').encode('utf-8')
        
        for i, byte in enumerate(filename_bytes):
            ih[AudioConstants.ENGINE_FILENAME_OFFSET + i] = byte
        
        # FLAC 데이터 저장
        for i, byte in enumerate(flac_data):
            ih[AudioConstants.ENGINE_FLAC_DATA_OFFSET + i] = byte
    
    def _add_event_data(self, ih: IntelHex, flac_data: bytes):
        """이벤트 사운드 데이터 추가 (FLAC 데이터만)"""
        for i, byte in enumerate(flac_data):
            ih[AudioConstants.EVENT_FLAC_DATA_OFFSET + i] = byte

class HexMerger:
    """HEX 데이터 병합 전용 클래스"""
    
    def __init__(self, sound_type: str, start_address: str):
        self.sound_type = sound_type
        self.start_address = int(start_address, 16)
    
    def merge_hex_data_list(self, hex_data_list: list, sound_positions: list = None) -> IntelHex:
        """HEX 데이터 리스트를 병합"""
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
        """이벤트 사운드 헤더 추가"""
        for _ in range(AudioConstants.EVENT_HEADER_SIZE):
            ih[current_address] = 0xFF
            current_address += 1
        return current_address
    
    def _add_engine_header(self, ih: IntelHex, current_address: int, sound_positions: list) -> int:
        """엔진 사운드 헤더 추가 (Magic Key + Sound Positions)"""
        # Magic Key 추가
        magic_key = AudioConstants.MAGIC_KEY
        ih[current_address] = magic_key & 0xFF
        ih[current_address + 1] = (magic_key >> 8) & 0xFF
        ih[current_address + 2] = (magic_key >> 16) & 0xFF
        ih[current_address + 3] = (magic_key >> 24) & 0xFF
        current_address += 4
        
        # Sound Positions 추가
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
        """이벤트 데이터 병합"""
        for temp_ih in hex_data_list:
            # 데이터 복사
            for address in range(temp_ih.minaddr(), temp_ih.maxaddr() + 1):
                ih[current_address] = temp_ih[address]
                current_address += 1
            
            # 4바이트 정렬을 위한 패딩
            current_address = self._add_padding(ih, current_address)
        
        return current_address
    
    def _merge_engine_data(self, ih: IntelHex, hex_data_list: list, current_address: int) -> int:
        """엔진 데이터 병합"""
        start_address = self.start_address
        
        for temp_ih in hex_data_list:
            # 데이터 복사
            for address in range(temp_ih.minaddr(), temp_ih.maxaddr() + 1):
                ih[current_address] = temp_ih[address]
                current_address += 1
            
            # 4바이트 정렬을 위한 패딩
            current_address = self._add_padding(ih, current_address)
        
        # 엔진 사운드의 경우 고정 크기로 패딩 (864KB)
        hex_file_size_bytes = int(864.0 * 1024)  # 864KB
        target_end_address = start_address + hex_file_size_bytes
        
        while current_address < target_end_address:
            ih[current_address] = 0xFF
            current_address += 1
        
        return current_address
    
    def _add_padding(self, ih: IntelHex, current_address: int) -> int:
        """4바이트 정렬을 위한 패딩 추가"""
        padding = current_address % AudioConstants.WORD_ALIGNMENT
        if padding != 0:
            padding_to_add = AudioConstants.WORD_ALIGNMENT - padding
            for _ in range(padding_to_add):
                ih[current_address] = 0xFF
                current_address += 1
        return current_address
    
    def get_hex_file_size(self) -> int:
        """병합된 HEX 파일 크기 계산"""
        # 이 메서드는 병합 후에 호출되어야 함
        return self.current_size if hasattr(self, 'current_size') else 0 
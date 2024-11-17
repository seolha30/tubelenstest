from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QRadioButton, QComboBox, QLineEdit, QListWidget, 
                            QLabel, QMessageBox, QFileDialog, QListWidgetItem)
import os
import yt_dlp
import re

class DownloaderUI(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.downloader = YoutubeDownloader(os.path.expanduser("~/Downloads"))
        self.setup_ui()
        self.connect_signals()
        
        # 창 스타일 설정
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 타이틀
        title_label = QLabel("Tube Down")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # URL 입력
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("YouTube URL 입력")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # 포맷 선택
        self.mp4_radio = QRadioButton("비디오 MP4")
        self.mp3_radio = QRadioButton("오디오 MP3 (320k)")
        self.mp4_radio.setChecked(True)
        layout.addWidget(self.mp4_radio)
        layout.addWidget(self.mp3_radio)
        
        # 화질 선택
        quality_layout = QHBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "720p", "480p", "360p"])
        quality_layout.addWidget(QLabel("화질 선택:"))
        quality_layout.addWidget(self.quality_combo)
        layout.addLayout(quality_layout)
        
        # 다운로드 버튼
        self.download_btn = QPushButton("다운로드 시작")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3d8ae0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.download_btn)
        
        # 다운로드 목록
        layout.addWidget(QLabel("다운로드 목록"))
        self.download_list = QListWidget()
        layout.addWidget(self.download_list)
        
        # 저장 경로
        path_layout = QHBoxLayout()
        self.path_label = QLabel(f"📂 {os.path.expanduser('~/Downloads')}")
        self.path_btn = QPushButton("변경")
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_btn)
        layout.addLayout(path_layout)
        
        # 창 크기 설정
        self.setFixedWidth(300)
        
    def connect_signals(self):
        # 다운로더 시그널 연결
        self.downloader.progress_signal.connect(self.update_progress)
        self.downloader.finished_signal.connect(self.download_finished)
        self.downloader.error_signal.connect(self.show_error)
        
        # 버튼 시그널 연결
        self.download_btn.clicked.connect(self.start_download)
        self.path_btn.clicked.connect(self.change_path)
        self.mp3_radio.toggled.connect(self.toggle_quality)
        
        # 메인 윈도우 이동 감지
        self.main_window.moveEvent = self.follow_main_window
        
    def follow_main_window(self, event):
        """메인 윈도우 이동시 따라가기"""
        if self.isVisible():
            main_geo = self.main_window.geometry()
            self.move(main_geo.right(), main_geo.top())
        
    def toggle_quality(self, checked):
        """MP3 선택시 화질 선택 비활성화"""
        self.quality_combo.setEnabled(not checked)
        
    def update_selected_count(self, count):
        """선택된 항목 수 업데이트"""
        self.download_btn.setText(f"다운로드 시작 ({count})")
        self.download_btn.setEnabled(count > 0)
        
    def start_download(self):
        """다운로드 시작"""
        url = self.url_input.text().strip()
        if not url and not hasattr(self, 'selected_urls'):
            QMessageBox.warning(self, "알림", "URL을 입력하거나 영상을 선택하세요.")
            return
            
        format_type = 'mp3' if self.mp3_radio.isChecked() else 'mp4'
        urls = [url] if url else self.selected_urls
        
        for url in urls:
            self.downloader.download_video(url, format_type)
            
    def update_progress(self, status, percentage):
        """진행률 업데이트"""
        # 이 부분을 수정
        items = self.download_list.findItems(status.split('%')[0], Qt.MatchFlag.MatchStartsWith)
        if items:
            item = items[0]
        else:
            item = QListWidgetItem(status)  # QListWidget -> QListWidgetItem으로 수정
            self.download_list.addItem(item)
        item.setText(f"{status}")
        
    def download_finished(self, message):
        """다운로드 완료"""
        QMessageBox.information(self, "완료", message)
        
    def show_error(self, message):
        """에러 표시"""
        QMessageBox.warning(self, "오류", message)
        
    def change_path(self):
        """저장 경로 변경"""
        path = QFileDialog.getExistingDirectory(self, "저장 경로 선택", self.downloader.download_path)
        if path:
            self.downloader.download_path = path
            self.path_label.setText(f"📂 {path}")

class DownloadWorker(QThread):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, format_type, download_path):
        super().__init__()
        self.url = url
        self.format_type = format_type
        self.download_path = download_path
        
    def sanitize_filename(self, filename):
        """파일 이름에서 유효하지 않은 문자 제거 및 공백 처리"""
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        filename = re.sub(r'\s+', " ", filename)
        return filename.strip()
        
    def run(self):
        try:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    
                    if total > 0:
                        percentage = (downloaded / total) * 100
                        # MP3의 경우 다운로드는 50%까지만 표시
                        if self.format_type == 'mp3':
                            percentage = percentage * 0.5  # 50%까지만
                        status = f"다운로드 중... {percentage:.0f}%"
                        self.progress_signal.emit(status, int(percentage))
                    else:
                        self.progress_signal.emit("다운로드 준비중...", 0)
                        
                elif d['status'] == 'finished':
                    if self.format_type == 'mp4':
                        self.progress_signal.emit("변환 작업중...", 99)
                    else:  # MP3의 경우
                        self.progress_signal.emit("MP3로 변환 중...", 50)
                        
                elif d['status'] == 'postprocessing':  # MP3 변환 과정 추가
                    if self.format_type == 'mp3':
                        percentage = 50 + (float(d.get('postprocessor_progress', 0)) * 50)  # 50~100%
                        self.progress_signal.emit(f"MP3로 변환 중... {percentage:.0f}%", int(percentage))

            # 영상 정보 가져오기
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                self.progress_signal.emit("영상 정보를 가져오는 중...", 0)
                info = ydl.extract_info(self.url, download=False)
                video_title = info.get('title', '')
                safe_title = self.sanitize_filename(video_title)
            
            # 다운로드 옵션 설정
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if self.format_type == 'mp4' else 'bestaudio/best',
                'outtmpl': os.path.join(self.download_path, f'{safe_title}.%(ext)s'),
                'progress_hooks': [progress_hook],
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }] if self.format_type == 'mp4' else [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
            }
            
            # 다운로드 실행
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            # 완료 메시지
            completion_message = "동영상 다운로드 완료!" if self.format_type == 'mp4' else "음원 다운로드 완료!"
            self.finished_signal.emit(completion_message)
            
        except Exception as e:
            self.error_signal.emit("다운로드 실패")

class YoutubeDownloader(QObject):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, download_path):
        super().__init__()
        self.download_path = download_path
        self.worker = None
        
    def download_video(self, url, format_type):
        """비디오 또는 오디오 다운로드"""
        self.worker = DownloadWorker(url, format_type, self.download_path)
        self.worker.progress_signal.connect(self.progress_signal)
        self.worker.finished_signal.connect(self.finished_signal)
        self.worker.error_signal.connect(self.error_signal)
        self.worker.start()

    async def batch_download(self, urls, download_type="video"):
        """일괄 다운로드"""
        try:
            for i, url in enumerate(urls, 1):
                self.progress_signal.emit(f"전체 진행률: {i}/{len(urls)}", int((i/len(urls))*100))
                format_type = 'mp4' if download_type == "video" else 'mp3'
                self.download_video(url, format_type)
                    
            self.finished_signal.emit("모든 다운로드가 완료되었습니다.")
            
        except Exception as e:
            self.error_signal.emit(str(e))

# 플러그인 클래스
class TubeLensPlugin:
    def __init__(self):
        print("플러그인 초기화 시작")
        self.name = "YouTube Downloader"
        self.version = "1.0"
        self.description = "YouTube 영상/음원 다운로더"
        self.downloader_ui = None
        self.auto_start = True
        print("플러그인 __init__ 완료")
        
    def initialize(self, app):
        """플러그인 초기화"""
        try:
            print(f"initialize 시작: app = {app}")
            self.downloader_ui = DownloaderUI(app)
            if self.auto_start:
                self.downloader_ui.show()
                main_geo = app.geometry()
                self.downloader_ui.move(main_geo.right(), main_geo.top())
            print("플러그인 initialize 성공")
            return True
        except Exception as e:
            print(f"플러그인 초기화 오류: {str(e)}")
            return False
            
    def cleanup(self):
        """플러그인 정리"""
        if self.downloader_ui:
            self.downloader_ui.close()
            self.downloader_ui = None

# 파일 맨 마지막에
if __name__ == "__main__":
    plugin = TubeLensPlugin()
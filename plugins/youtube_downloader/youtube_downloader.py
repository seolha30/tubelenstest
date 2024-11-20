from PyQt6.QtGui import QPixmap, QColor, QPainter, QPainterPath, QDesktopServices, QCursor
from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt, QPoint, QEvent
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QRadioButton, QComboBox, QLineEdit, QLabel, 
                            QMessageBox, QFileDialog, QGroupBox, QProgressBar)
import os
import yt_dlp
import re

class DownloaderUI(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.downloader = YoutubeDownloader(os.path.join(os.path.expanduser('~'), 'Desktop'))
        self.drag_position = None
        self.selected_urls = []
        
        # UI 초기화 전에 윈도우 상태 설정
        self.setup_window_flags()
        
        # 메인 윈도우 위치와 크기 가져오기
        if hasattr(main_window, 'geometry'):
            main_geo = main_window.geometry()
            self.move(main_geo.right(), main_geo.top())
            
            # 크기 설정은 UI 초기화 후에
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.resize(200, main_geo.height()))
            
        self.setup_ui()
        self.connect_signals()

    def setup_window_flags(self):
        flags = (
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool  # Tool 플래그 추가
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)  # 메인창 종료시 함께 종료
        
        # 메인 윈도우가 닫힐 때 이 창도 함께 닫히도록 설정
        if hasattr(self.main_window, 'destroyed'):
            self.main_window.destroyed.connect(self.close)

        # 테두리와 배경 설정
        self.setStyleSheet("""
            QWidget#DownloaderUI {
                background-color: #1a1a1a;
                border: 1px solid #4a9eff;
                border-radius: 5px;
            }
        """)
        self.setObjectName("DownloaderUI")
       
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)  # 테두리가 잘 보이도록 여백 최소화
        layout.setSpacing(15)  # 그룹박스 간격 늘림
        
        # 스타일 설정
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QRadioButton {
                color: #ffffff;
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 13px;
                height: 13px;
            }
            QComboBox {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d8ae0;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
            QPushButton#stopButton {
                background-color: #ff4a4a;
            }
            QPushButton#stopButton:hover {
                background-color: #e04a4a;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                background-color: #3b3b3b;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 3px;
            }
            QGroupBox {
                border: 1px solid #4a9eff;
                border-radius: 4px;
                margin-top: 3px;
                padding-top: 8px;
                color: #4a9eff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        
        # 타이틀 영역 (고정 영역)
        self.fixed_container = QWidget()  # self 추가
        self.fixed_container.setFixedHeight(90)
        self.fixed_container.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-bottom: 1px solid #4a9eff;
            }
        """)
        self.fixed_container.setObjectName("fixed_container")  # 객체 이름 설정

        fixed_layout = QVBoxLayout(self.fixed_container)
        fixed_layout.setSpacing(0)
        fixed_layout.setContentsMargins(0, 5, 0, 5)

        # 제목
        title_label = QLabel("Tube Down")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #4a9eff;
            padding: 5px 0;
            background: transparent;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fixed_layout.addWidget(title_label)

        # 접기/펼치기 버튼
        self.toggle_button = QPushButton("🔼 접기")
        self.toggle_button.setFixedSize(100, 30)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4a9eff;
                border: none;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                margin: 0px;
            }
            QPushButton:hover {
                color: #3d8ae0;
            }
        """)
        self.is_collapsed = False
        self.toggle_button.clicked.connect(self.toggle_collapse)
        fixed_layout.addWidget(self.toggle_button, 0, Qt.AlignmentFlag.AlignCenter)

        # 메인 레이아웃에 추가
        self.layout().addWidget(self.fixed_container)
        
        # URL 입력 영역
        url_group = QGroupBox("URL로 다운로드")
        url_layout = QVBoxLayout(url_group)
        url_layout.setSpacing(3)

        # URL 입력창
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("YouTube URL 입력")
        self.url_input.setFixedWidth(180)
        url_layout.addWidget(self.url_input, 0, Qt.AlignmentFlag.AlignCenter)

        # URL 다운로드 버튼
        self.url_download_btn = QPushButton("URL 영상받기")
        self.url_download_btn.setFixedWidth(180)
        url_layout.addWidget(self.url_download_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(url_group)
        layout.addSpacing(10)
        
        
        # 옵션 그룹
        options_group = QGroupBox("다운로드 옵션")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(3)
        
        # 선택된 URL 수 표시를 옵션 그룹 안으로 이동
        self.selected_count_label = QLabel("선택된 영상: 0개")
        options_layout.addWidget(self.selected_count_label)
        
        # 포맷 선택
        self.mp4_radio = QRadioButton("비디오 MP4 (최고화질)")
        self.mp3_radio = QRadioButton("오디오 MP3 (320k)")
        self.mp4_radio.setChecked(True)
        options_layout.addWidget(self.mp4_radio)
        options_layout.addWidget(self.mp3_radio)
        options_layout.addSpacing(5)  # 라디오 버튼과 다운로드 버튼 사이 약간의 여백

        # 다운로드 버튼들
        self.select_download_btn = QPushButton("선택 영상 받기")
        self.all_download_btn = QPushButton("전체 영상 받기")
        self.select_download_btn.setFixedWidth(180)
        self.all_download_btn.setFixedWidth(180)
        self.select_download_btn.setEnabled(False)  # 초기에는 비활성화
        options_layout.addWidget(self.select_download_btn, 0, Qt.AlignmentFlag.AlignCenter)
        options_layout.addWidget(self.all_download_btn, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(options_group)
        layout.addSpacing(5)  # 그룹박스 사이 여백 줄임
        
        # 진행률 표시 그룹
        progress_group = QGroupBox("다운로드 진행률")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(3)
        
        self.progress_label = QLabel("대기중...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_group)
        layout.addSpacing(10)
        
        # 저장 경로
        path_group = QGroupBox("저장 경로")
        path_layout = QHBoxLayout(path_group)
        path_layout.setSpacing(3)
        self.path_label = QLabel(f"📂 {os.path.expanduser('~/Desktop')}")
        self.path_btn = QPushButton("변경")
        self.path_btn.setFixedWidth(60)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_btn)
        layout.addWidget(path_group)
        layout.addSpacing(10)
        
        # 나머지 공간을 위로 밀어주기 위한 스트레치
        layout.addStretch()

    def connect_signals(self):
        self.downloader.progress_signal.connect(self.update_progress)
        self.downloader.error_signal.connect(self.show_error)
        self.downloader.all_completed_signal.connect(self.all_downloads_completed)
        self.select_download_btn.clicked.connect(self.start_selected_download)
        self.all_download_btn.clicked.connect(self.start_all_download)
        self.path_btn.clicked.connect(self.change_path)
        
        self.url_download_btn.clicked.connect(self.start_url_download)  # URL 다운로드 버튼
        self.url_input.returnPressed.connect(self.start_url_download)  # 엔터키
        self.url_input.textChanged.connect(self.update_button_states)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedHeight(90)  # 고정 영역 높이만큼
            self.toggle_button.setText("🔽 펼치기")
            # fixed_container를 제외한 다른 위젯들 숨기기
            for i in range(self.layout().count()):
                widget = self.layout().itemAt(i).widget()
                if widget and widget != self.fixed_container:
                    widget.hide()
        else:
            self.setFixedHeight(800)  # 원래 높이로 복구
            self.toggle_button.setText("🔼 접기")
            # 모든 위젯 보이기
            for i in range(self.layout().count()):
                widget = self.layout().itemAt(i).widget()
                if widget:
                    widget.show()
    
    def update_button_states(self):
        """URL 입력 상태에 따라 버튼 상태 업데이트"""
        has_url = bool(self.url_input.text().strip())
        
        # URL 다운로드 버튼은 항상 활성화
        self.url_download_btn.setEnabled(True)
        
        # 선택된 영상이 있으면
        if len(self.selected_urls) > 0:
            self.select_download_btn.setEnabled(True)
            self.all_download_btn.setEnabled(False)
        # 기본 상태 (전체 다운로드만 가능)
        else:
            self.select_download_btn.setEnabled(False)
            self.all_download_btn.setEnabled(True)
    
    def start_url_download(self):
        """URL 입력으로 다운로드 시작"""
        if self.url_download_btn.text() == "중지":
            self.downloader.stop_downloads()
            self.reset_ui()
            return

        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "경고", "URL을 입력해주세요.")
            return

        try:
            # YouTube URL 유효성 검사
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                ydl.extract_info(url, download=False)
                
            # 다운로드 시작
            format_type = 'mp3' if self.mp3_radio.isChecked() else 'mp4'
            self.downloader.total_downloads = 1
            self.downloader.download_video(url, format_type)
            
            # 버튼 상태 변경
            self.url_download_btn.setText("중지")
            self.url_download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4a4a;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e04a4a;
                }
            """)
            
            # 다른 버튼들 비활성화
            self.select_download_btn.setEnabled(False)
            self.all_download_btn.setEnabled(False)
            
        except Exception as e:
            QMessageBox.warning(self, "오류", "올바른 YouTube URL이 아닙니다.")
    
    def set_selected_urls(self, urls):
        if hasattr(self.main_window, 'table'):
            # 현재 화면에 보이는 행만 필터링
            visible_urls = []
            for row in range(self.main_window.table.rowCount()):
                if not self.main_window.table.isRowHidden(row):  # 필터링되어 보이는 항목만
                    item = self.main_window.table.item(row, 0)  # N열 체크
                    if item and item.background().color() == QColor("#FF5D5D"):
                        video_data = self.main_window.search_results[row]
                        if 'video_url' in video_data:
                            visible_urls.append(video_data['video_url'])
            
            self.selected_urls = visible_urls
            self.update_selected_count(len(self.selected_urls))
            self.select_download_btn.setEnabled(len(self.selected_urls) > 0)
            self.all_download_btn.setEnabled(len(self.selected_urls) == 0) 
            
        if len(self.selected_urls) > 0:
            self.select_download_btn.setEnabled(True)
            self.all_download_btn.setEnabled(False)
        else:
            self.select_download_btn.setEnabled(False)
            self.all_download_btn.setEnabled(True)  
                

    def update_selected_count(self, count):
        self.selected_count_label.setText(f"선택된 영상: {count}개")
        
    def start_selected_download(self):
        if self.select_download_btn.text() == "중지":
            self.downloader.stop_downloads()
            self.reset_ui()
            return

        if not self.selected_urls:
            QMessageBox.warning(self, "경고", "선택된 영상이 없습니다.")
            return
        
        self.start_download(self.selected_urls)
        self.select_download_btn.setText("중지")
        self.select_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4a4a;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e04a4a;
            }
        """)
        self.all_download_btn.setEnabled(False)
        
    def start_all_download(self):
        if self.all_download_btn.text() == "중지":
            self.downloader.stop_downloads()
            self.reset_ui()
            return
        
        print("전체 다운로드 시작 시도")  # 디버깅 1
        
        if not hasattr(self.main_window, 'search_results'):
            print("search_results 없음")  # 디버깅 2
            QMessageBox.warning(self, "경고", "다운로드할 영상이 없습니다.")
            return
            
        if len(self.selected_urls) > 0:
            print(f"선택된 URL이 있음: {len(self.selected_urls)}개")  # 디버깅 3
            return
            
        try:
            print(f"테이블 행 수: {self.main_window.table.rowCount()}")  # 디버깅 4
            visible_urls = []
            
            for i, result in enumerate(self.main_window.search_results):
                is_hidden = self.main_window.table.isRowHidden(i)
                print(f"행 {i}: 숨김={is_hidden}")  # 디버깅 5
                
                if not is_hidden:
                    url = result.get('video_url')
                    if url:
                        visible_urls.append(url)
                        print(f"URL 추가됨: {url}")  # 디버깅 6
            
            print(f"수집된 URL 수: {len(visible_urls)}")  # 디버깅 7
            
            if not visible_urls:
                print("다운로드할 URL 없음")  # 디버깅 8
                QMessageBox.warning(self, "경고", "다운로드할 영상이 없습니다.")
                return
            
            print("다운로드 시작 직전")  # 디버깅 9
            self.start_download(visible_urls)
            self.all_download_btn.setText("중지")
            self.all_download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4a4a;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e04a4a;
                }
            """)
            self.select_download_btn.setEnabled(False)
            
        except Exception as e:
            print(f"오류 발생: {str(e)}")  # 디버깅 10
            QMessageBox.warning(self, "오류", f"다운로드 준비 중 오류가 발생했습니다: {str(e)}")
    
    def start_download(self, urls):
        format_type = 'mp3' if self.mp3_radio.isChecked() else 'mp4'
        self.downloader.total_downloads = len(urls)
        
        for url in urls:
            self.downloader.download_video(url, format_type)
    
    def all_downloads_completed(self, count):
        QMessageBox.information(self, "완료", f"모든 다운로드가 완료되었습니다. (총 {count}개)")
        self.reset_ui()
    
    def reset_ui(self):
        """UI 상태 초기화"""
        self.progress_bar.setValue(0)
        self.progress_label.setText("대기중...")
        
        # 모든 버튼 텍스트 원래대로
        self.url_download_btn.setText("URL 영상받기")
        self.select_download_btn.setText("선택 영상 받기")
        self.all_download_btn.setText("전체 영상 받기")
        
        # 버튼 스타일 초기화
        default_style = """
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d8ae0;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
        """
        self.url_download_btn.setStyleSheet(default_style)
        self.select_download_btn.setStyleSheet(default_style)
        self.all_download_btn.setStyleSheet(default_style)
        
        # URL 다운로드 버튼은 항상 활성화
        self.url_download_btn.setEnabled(True)
        
        # 선택된 영상이 있을 때
        if len(self.selected_urls) > 0:
            self.select_download_btn.setEnabled(True)
            self.all_download_btn.setEnabled(False)
        # 기본 상태 (전체 다운로드만 가능)
        else:
            self.select_download_btn.setEnabled(False)
            self.all_download_btn.setEnabled(True)
    
    def update_progress(self, status, percentage):
        self.progress_label.setText(status)
        self.progress_bar.setValue(percentage)
    
    def show_error(self, message):
        QMessageBox.warning(self, "오류", message)
        self.reset_ui()
        
    def change_path(self):
        path = QFileDialog.getExistingDirectory(self, "저장 경로 선택", self.downloader.download_path)
        if path:
            self.downloader.download_path = path
            self.path_label.setText(f"📂 {path}")
            
    
            
    def follow_main_window(self, event=None):
        if self.main_window and self.isVisible():
            main_geo = self.main_window.geometry()
            new_x = main_geo.right()
            new_y = main_geo.top()
            self.move(new_x, new_y)

class DownloadWorker(QThread):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, format_type, download_path):  # 수정된 부분
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
                        if self.format_type == 'mp3':
                            percentage = percentage * 0.5
                        status = f"다운로드 중... {percentage:.0f}%"
                        self.progress_signal.emit(status, int(percentage))
                    else:
                        self.progress_signal.emit("다운로드 준비중...", 0)
                        
                elif d['status'] == 'finished':
                    if self.format_type == 'mp4':
                        self.progress_signal.emit("변환 작업중...", 99)
                    else:
                        self.progress_signal.emit("MP3로 변환 중...", 50)
                        
                elif d['status'] == 'postprocessing':
                    if self.format_type == 'mp3':
                        percentage = 50 + (float(d.get('postprocessor_progress', 0)) * 50)
                        self.progress_signal.emit(f"MP3로 변환 중... {percentage:.0f}%", int(percentage))

            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                self.progress_signal.emit("영상 정보를 가져오는 중...", 0)
                info = ydl.extract_info(self.url, download=False)
                video_title = info.get('title', '')
                safe_title = self.sanitize_filename(video_title)
            
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
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            
            completion_message = "동영상 다운로드 완료!" if self.format_type == 'mp4' else "음원 다운로드 완료!"
            self.finished_signal.emit(completion_message)
            
        except Exception as e:
            self.error_signal.emit(f"다운로드 실패: {str(e)}")
            
        finally:
            self.finished.emit()  # 작업 완료 시그널 발생    

class YoutubeDownloader(QObject):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    all_completed_signal = pyqtSignal(int)
    
    def __init__(self, download_path):
        super().__init__()
        self.download_path = download_path
        self.workers = []
        self.completed_count = 0
        self.total_downloads = 0
        self.max_concurrent = 4  # 최대 동시 다운로드 수
        self.queue = []  # 대기 중인 다운로드 큐
        
    def stop_downloads(self):
        """현재 진행 중인 모든 다운로드 중지"""
        # 대기 중인 다운로드 큐 비우기
        self.queue.clear()
        
        # 현재 실행 중인 모든 워커 중지
        for worker in self.workers:
            if hasattr(worker, 'terminate'):
                worker.terminate()
        
        # 워커 리스트 초기화
        self.workers.clear()
        
        # 다운로드 카운트 초기화
        self.completed_count = 0
        self.total_downloads = 0
        
    def download_video(self, url, format_type):
        """비디오 또는 오디오 다운로드"""
        if len(self.workers) < self.max_concurrent:
            self._start_download(url, format_type)
        else:
            self.queue.append((url, format_type))
            
    def _start_download(self, url, format_type):
        """실제 다운로드 시작"""
        worker = DownloadWorker(url, format_type, self.download_path)  # 수정된 부분
        worker.progress_signal.connect(self.progress_signal)
        worker.finished_signal.connect(lambda msg: self._handle_completion(msg, worker))
        worker.error_signal.connect(self.error_signal)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.workers.append(worker)
        worker.start()
        
    def _handle_completion(self, message, worker):
        """다운로드 완료 처리"""
        self.completed_count += 1
        
        # 대기 중인 다운로드가 있으면 시작
        if self.queue:
            url, format_type = self.queue.pop(0)
            self._start_download(url, format_type)
            
        # 모든 다운로드가 완료되었는지 확인
        if self.completed_count == self.total_downloads:
            self.all_completed_signal.emit(self.completed_count)
            self.completed_count = 0
            self.total_downloads = 0
            
    def _cleanup_worker(self, worker):
        """완료된 작업 정리"""
        if worker in self.workers:
            self.workers.remove(worker)

class TubeLensPlugin:
    def __init__(self):
        self.name = "YouTube Downloader"
        self.version = "1.0"
        self.description = "YouTube 영상/음원 다운로더"
        self.downloader_ui = None
        self.auto_start = True
        self.app = None
        
    def initialize(self, app):
        try:
            self.app = app
            self.setup_event_handling(app)
            
            # UI 생성 및 표시
            if self.downloader_ui:
                self.downloader_ui.deleteLater()
            self.downloader_ui = DownloaderUI(app)
            
            if self.auto_start:
                from PyQt6.QtCore import QTimer
                # 약간의 지연 후 표시
                QTimer.singleShot(100, self.show_downloader)
            
            return True
        except Exception as e:
            print(f"플러그인 초기화 오류: {str(e)}")
            return False

    def setup_event_handling(self, app):
        if not hasattr(app, '_original_move_event'):
            app._original_move_event = app.moveEvent
            
        if not hasattr(app, '_original_activate_event'):
            app._original_activate_event = app.changeEvent

        def new_move_event(event):
            if hasattr(app, '_original_move_event'):
                app._original_move_event(event)
            if self.downloader_ui and self.downloader_ui.isVisible():
                self.downloader_ui.follow_main_window()
                
        def new_change_event(event):
            if hasattr(app, '_original_activate_event'):
                app._original_activate_event(event)
            if event.type() == QEvent.Type.ActivationChange:
                if self.downloader_ui and self.downloader_ui.isVisible():
                    if app.isActiveWindow():
                        self.downloader_ui.raise_()
                    else:
                        self.downloader_ui.lower()
        
        app.moveEvent = new_move_event
        app.changeEvent = new_change_event

    def show_downloader(self):
        if self.downloader_ui:
            self.downloader_ui.show()
            self.downloader_ui.follow_main_window()

    def eventFilter(self, source, event):
        if source == self.app:
            if event.type() == Qt.WindowType.Move:
                if self.downloader_ui and hasattr(self.app, 'geometry'):
                    main_geo = self.app.geometry()
                    self.downloader_ui.move(main_geo.right(), main_geo.top())
        return super().eventFilter(source, event)
    
    def on_selection_changed(self, urls):
        """튜브렌즈에서 선택이 변경될 때 호출"""
        print(f"플러그인의 on_selection_changed 호출됨: {urls}")  # 디버깅용
        if self.downloader_ui:
            self.downloader_ui.set_selected_urls(urls)
            print("다운로더 UI에 URLs 전달 완료")  # 디버깅용
            
    def cleanup(self):
        try:
            # 이벤트 핸들러 복원
            if hasattr(self.app, '_original_move_event'):
                self.app.moveEvent = self.app._original_move_event
                delattr(self.app, '_original_move_event')
            if hasattr(self.app, '_original_activate_event'):
                self.app.changeEvent = self.app._original_activate_event
                delattr(self.app, '_original_activate_event')
                
            # 다운로더 UI 정리
            if self.downloader_ui:
                self.downloader_ui.close()
                self.downloader_ui.deleteLater()
                self.downloader_ui = None
                
            # 참조 제거    
            self.app = None
                
        except Exception as e:
            print(f"cleanup 오류: {str(e)}")

if __name__ == "__main__":
    plugin = TubeLensPlugin()
class TubeLensPlugin:
    def __init__(self):
        self.name = "테스트 플러그인"
        self.version = "1.0"
        self.description = "튜브렌즈 플러그인 테스트용"
    
    def initialize(self, app):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(app, "테스트", "테스트 플러그인이 설치되었습니다!")
        return True
    
    def cleanup(self):
        pass

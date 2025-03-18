from PyQt5.QtCore import QThread, pyqtSignal

class BackgroundLoader(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    
    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks
        
    def run(self):
        for task in self.tasks:
            self.progress.emit(f"Loading {task.__name__}...")
            task()
        self.finished.emit()
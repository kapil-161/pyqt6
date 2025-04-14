from PyQt6.QtCore import QThread, pyqtSignal
from typing import Any, Callable, Dict, List, Optional
import traceback

class BackgroundLoader(QThread):
    finished = pyqtSignal(object)  # Emits result data
    error = pyqtSignal(str)  # Emits error messages
    progress = pyqtSignal(str, int)  # Emits (message, percentage)
    
    def __init__(self, worker_function: Callable, *args, **kwargs):
        super().__init__()
        self.worker_function = worker_function
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self._is_cancelled = False

    def run(self):
        try:
            self.result = self.worker_function(
                *self.args,
                progress_callback=self._progress_callback,
                **self.kwargs
            )
            if not self._is_cancelled:
                self.finished.emit(self.result)
        except Exception as e:
            self.error.emit(f"Error: {str(e)}\n{traceback.format_exc()}")

    def cancel(self):
        self._is_cancelled = True
        self.wait()

    def _progress_callback(self, message: str, percentage: int):
        self.progress.emit(message, percentage)
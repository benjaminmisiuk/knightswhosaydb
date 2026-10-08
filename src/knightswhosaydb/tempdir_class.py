import os
import shutil
import time
from pathlib import Path
import gc

class TempDir:
    def __init__(self, base_path, save_lines):
        base = Path(base_path) if base_path else Path.cwd()
        self._path = base / "temp"
        self.save_lines = save_lines

    def __enter__(self):
        os.makedirs(self._path, exist_ok=True)
        return self  # Returns the object itself so you can call its methods

    def path(self) -> Path:
        return self._path

    def str(self) -> str:
        return str(self._path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        gc.collect()
        
        if not self.save_lines:
            time.sleep(0.1)
            try:
                shutil.rmtree(self._path)
            except PermissionError:
                shutil.rmtree(self._path, ignore_errors=True)
        else:
            print(f'Lines saved to: {self._path}')
        return False
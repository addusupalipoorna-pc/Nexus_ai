import os
import sys

# ── CRITICAL: Always run from the directory containing app.py ──────────────────
# This ensures relative paths (models/, database/, etc.) work when the app is
# launched from File Manager, desktop shortcut, taskbar, or VBS double-click.
_app_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_app_dir)
sys.path.insert(0, _app_dir)

# ── Auto-re-execute using the virtual environment's Python if run on system Python ──
_venv_python = os.path.join(_app_dir, ".venv", "Scripts", "python.exe")
_venv_pythonw = os.path.join(_app_dir, ".venv", "Scripts", "pythonw.exe")
_current_python = os.path.abspath(sys.executable).lower()

if os.path.exists(_venv_python) and _current_python != os.path.abspath(_venv_python).lower() and _current_python != os.path.abspath(_venv_pythonw).lower():
    import subprocess
    sys.exit(subprocess.call([_venv_python] + sys.argv))

# ── Environment fixes (must be set before any DLL / cv2 import) ───────────────
# Prevent crash when multiple OpenMP runtimes are loaded (torch + cv2 + mediapipe)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
# Suppress verbose OpenCV videoio / backend discovery noise
os.environ.setdefault("OPENCV_VIDEOIO_DEBUG", "0")
# Ensure the app directory is on PATH so any bundled DLLs can be found
if _app_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _app_dir + os.pathsep + os.environ.get("PATH", "")



from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from database.logger import DatabaseLogger
from core.engine import InferenceEngine
from ui.main_window import MainWindow

def setup_workspace_folders(root_dir):
    """Generates all target system folders if they do not already exist."""
    folders = ["models", "database", "recordings", "screenshots", "exports"]
    for f in folders:
        os.makedirs(os.path.join(root_dir, f), exist_ok=True)

def main():
    # Initialize workspace root
    root_dir = os.path.dirname(os.path.abspath(__file__))
    setup_workspace_folders(root_dir)
    
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    
    # Global QSS Stylesheet Layout (frosted glassmorphism, obsidian dark, cyan/crimson neon accent lines)
    global_stylesheet = """
        QMainWindow {
            background-color: #0B0F19;
        }
        
        /* Glassmorphism containment widgets */
        QFrame#panel_containment {
            background-color: rgba(22, 27, 38, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
        }
        
        /* Custom styled scrollbars */
        QScrollBar:vertical {
            border: none;
            background: #0B0F19;
            width: 8px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: rgba(255, 255, 255, 0.1);
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #00E5FF;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        
        QScrollBar:horizontal {
            border: none;
            background: #0B0F19;
            height: 8px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: rgba(255, 255, 255, 0.1);
            min-width: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #00E5FF;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
        }
    """
    app.setStyleSheet(global_stylesheet)

    # Initialize Asynchronous Logger Database
    db_logger = DatabaseLogger()
    
    # Authenticate Operator
    bypass_auth = "--no-auth" in sys.argv or os.environ.get("NEXUS_BYPASS_AUTH") == "1"
    if not bypass_auth:
        from ui.login_dialog import LoginDialog
        login_dlg = LoginDialog(db_logger)
        if login_dlg.exec() != LoginDialog.DialogCode.Accepted:
            db_logger.close()
            sys.exit(0)
        
    # Initialize multi-threaded QThread worker
    engine = InferenceEngine(db_logger)
    
    # Construct frameless main window shell
    window = MainWindow(db_logger, engine)
    window.show()
    
    # Execute application loop
    sys_exit_code = app.exec()
    
    # Graceful database logging shutdown
    db_logger.close()
    
    sys.exit(sys_exit_code)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        from datetime import datetime
        error_msg = traceback.format_exc()
        try:
            with open("run.log", "a") as f:
                f.write(f"\n[CRITICAL STARTUP ERROR] {datetime.now()}:\n{error_msg}\n")
        except Exception:
            pass
        # Display message box using ctypes on Windows
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, 
                f"NEXUS AI failed to start.\n\nError: {e}\n\nCheck run.log for full traceback.", 
                "NEXUS AI - Startup Error", 
                0x10
            )
        except Exception:
            pass
        sys.exit(1)


import os
import sys

# Set duplicate OpenMP library initialization policy to prevent C++ crashes on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add workspace to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    main()

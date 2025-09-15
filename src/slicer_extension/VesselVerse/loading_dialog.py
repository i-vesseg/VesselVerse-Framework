import qt, slicer
from slicer.ScriptedLoadableModule import *

class loading_dialog(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Loading Dialog"
        self.parent.categories = ["Utilities"]
        self.parent.contributors = ["Daniele Falcetta (EURECOM - Biot, France)"]

class loading_dialogWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

class ProcessingDialog(qt.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Configure dialog appearance
        self.setWindowTitle("Processing")
        self.setWindowFlags(qt.Qt.Dialog | qt.Qt.CustomizeWindowHint | qt.Qt.WindowTitleHint)
        self.setModal(True)
        self.setFixedSize(300, 100)
        
        # Create layout
        layout = qt.QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Create progress indicator
        self.progressBar = self.create_progress_bar()
        layout.addWidget(self.progressBar)
        
        # Create status label
        self.statusLabel = self.create_status_label()
        layout.addWidget(self.statusLabel)
        
        # Apply styling
        self.apply_styles()
        
    def create_progress_bar(self):
        progressBar = qt.QProgressBar()
        progressBar.setMinimum(0)
        progressBar.setMaximum(0)  # Indeterminate progress
        progressBar.setTextVisible(False)
        return progressBar
        
    def create_status_label(self):
        label = qt.QLabel("Computing intersection between segmentations...")
        label.setAlignment(qt.Qt.AlignCenter)
        return label
        
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
            QLabel {
                color: #424242;
                font-size: 12px;
            }
        """)
        
    def update_status(self, message):
        """Update the status message."""
        self.statusLabel.setText(message)
        slicer.app.processEvents()  # Ensure UI updates
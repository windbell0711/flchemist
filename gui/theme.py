def dark_stylesheet() -> str:
    qss = """
    QMainWindow, QDialog {
        background-color: #1e1e1e;
        color: #e0e0e0;
        font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    }
    QWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    QLabel {
        color: #e0e0e0;
        font-size: 12px;
    }
    QPushButton {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 12px;
        min-height: 24px;
    }
    QPushButton:hover {
        background-color: #3c3c3c;
        border-color: #0078d4;
    }
    QPushButton:pressed {
        background-color: #0078d4;
    }
    QPushButton:disabled {
        background-color: #252525;
        color: #555555;
        border-color: #2d2d2d;
    }
    QPushButton#phase-button {
        font-size: 16px;
        font-weight: bold;
        padding: 18px 40px;
        border-radius: 10px;
        min-width: 200px;
    }
    QPushButton#accent-button {
        background-color: #0078d4;
        border-color: #0078d4;
        color: #ffffff;
    }
    QPushButton#accent-button:hover {
        background-color: #1a8ae8;
    }
    QPushButton#accent-button:disabled {
        background-color: #1a3a5c;
        color: #666666;
        border-color: #1a3a5c;
    }
    QLineEdit {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
    }
    QLineEdit:focus {
        border-color: #0078d4;
    }
    QPlainTextEdit {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
    }
    QPlainTextEdit:focus {
        border-color: #0078d4;
    }
    QRadioButton {
        color: #e0e0e0;
        font-size: 12px;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 16px;
        height: 16px;
        border-radius: 8px;
        border: 2px solid #555555;
        background-color: #2d2d2d;
    }
    QRadioButton::indicator:checked {
        background-color: #0078d4;
        border-color: #0078d4;
    }
    QCheckBox {
        color: #e0e0e0;
        font-size: 12px;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border-radius: 3px;
        border: 2px solid #555555;
        background-color: #2d2d2d;
    }
    QCheckBox::indicator:checked {
        background-color: #0078d4;
        border-color: #0078d4;
    }
    QGroupBox {
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 16px;
        font-size: 12px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        padding: 0 8px;
    }
    QTreeWidget {
        background-color: #252525;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        font-size: 12px;
    }
    QTreeWidget::item {
        padding: 4px 8px;
    }
    QTreeWidget::item:selected {
        background-color: #3c3c3c;
    }
    QHeaderView::section {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        padding: 6px;
        font-size: 12px;
        font-weight: bold;
    }
    QTableWidget {
        background-color: #252525;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        font-size: 12px;
        gridline-color: #333333;
    }
    QTableWidget::item {
        padding: 4px 8px;
    }
    QTableWidget::item:selected {
        background-color: #3c3c3c;
    }
    QProgressBar {
        background-color: #2d2d2d;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        text-align: center;
        color: #e0e0e0;
        font-size: 12px;
        height: 20px;
    }
    QProgressBar::chunk {
        background-color: #0078d4;
        border-radius: 3px;
    }
    QComboBox {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 12px;
    }
    QComboBox:focus {
        border-color: #0078d4;
    }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        selection-background-color: #0078d4;
    }
    QTextEdit {
        background-color: #252525;
        color: #e0e0e0;
        border: 1px solid #3c3c3c;
        border-radius: 4px;
        font-size: 12px;
    }
    QScrollBar:vertical {
        background-color: #2d2d2d;
        width: 10px; border: none;
    }
    QScrollBar::handle:vertical {
        background-color: #555555; border-radius: 5px; min-height: 30px;
    }
    QScrollBar::handle:vertical:hover { background-color: #0078d4; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal {
        background-color: #2d2d2d; height: 10px; border: none;
    }
    QScrollBar::handle:horizontal {
        background-color: #555555; border-radius: 5px; min-width: 30px;
    }
    QScrollBar::handle:horizontal:hover { background-color: #0078d4; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
    QMessageBox { background-color: #1e1e1e; color: #e0e0e0; }
    QMessageBox QLabel { color: #e0e0e0; }
    QMessageBox QPushButton { min-width: 80px; }
    QDialogButtonBox { background-color: #1e1e1e; }
    """
    return qss

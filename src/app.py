import sys
from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QLabel,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QSlider,
    QPushButton,
    QTableWidget,
    QHeaderView,
    QTableWidgetItem,
)

from PyQt6.QtGui import (
    QAction,
    QPalette,
    QColor,
    QPixmap,
    QMouseEvent,
    QKeyEvent,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject

from manualTracking import ManualTracking


class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def run(self):
        return


class Color(QWidget):
    def __init__(self, color):
        super(Color, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)


class MainWindow(QMainWindow):
    sliderWidget: QSlider
    sliderPlus: QPushButton
    sliderMinus: QPushButton
    scaledPixmap: QPixmap
    sliderStatus: QLabel
    mainVideoView: QLabel

    roiTable: QTableWidget
    roiTableHeader = ["Index", "x", "y"]

    thread: QThread

    tracking: ManualTracking

    def __init__(self):
        super(MainWindow, self).__init__()

        menu = self.menuBar()

        fileMenu = menu.addMenu("&File")

        exitAction = QAction("E&xit", self)
        exitAction.triggered.connect(self.onExitClicked)

        openFileAction = QAction("&Open", self)
        openFileAction.triggered.connect(self.onFileOpen)

        fileMenu.addAction(openFileAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)

        # Video View
        self.mainVideoView = QLabel()
        self.mainVideoView.setMinimumSize(1, 1)
        self.mainVideoView.mousePressEvent = self.mainVideoViewMousePressEvent

        # Bottom Menu

        self.sliderWidget = QSlider(Qt.Orientation.Horizontal, self)

        self.sliderWidget.setMinimum(1)
        self.sliderWidget.setMaximum(100)
        self.sliderWidget.setSingleStep(1)

        self.sliderMinus = QPushButton("-")
        self.sliderMinus.clicked.connect(self.sliderMinusClicked)
        self.sliderPlus = QPushButton("+")
        self.sliderPlus.clicked.connect(self.sliderPlusClicked)
        exportResult = QPushButton("Export Data")
        exportResult.clicked.connect(self.exportData)
        # self.sliderPlus.clicked.connect(self.sliderPlusClicked)

        self.sliderStatus = QLabel("Idle")

        self.sliderWidget.valueChanged.connect(self.sliderChanged)

        bottomMenuLayout = QVBoxLayout()
        bottomMenuSliderLayout = QHBoxLayout()
        bottomMenuSliderLayout.addWidget(self.sliderMinus)
        bottomMenuSliderLayout.addWidget(self.sliderWidget)
        bottomMenuSliderLayout.addWidget(self.sliderPlus)
        bottomMenuLayout.addLayout(bottomMenuSliderLayout)
        bottomMenuLayout.addWidget(self.sliderStatus)

        bottomMenu = QWidget()
        bottomMenu.setFixedHeight(75)
        bottomMenu.setLayout(bottomMenuLayout)
        # Set content

        contentLayout = QVBoxLayout()
        contentLayout.addWidget(self.mainVideoView)
        contentLayout.addWidget(bottomMenu)

        sideMenu = QWidget()
        sideMenu.setFixedWidth(250)

        sideMenuBottom = QWidget()
        sideMenuBottom.setFixedHeight(75)

        sideMenuBottomLayout = QGridLayout()
        sideMenuBottomLayout.addWidget(exportResult)
        sideMenuBottom.setLayout(sideMenuBottomLayout)

        self.roiTable = QTableWidget(0, 3)
        self.roiTable.setHorizontalHeaderLabels(self.roiTableHeader)
        self.roiTable.resizeColumnsToContents()
        self.roiTable.resizeRowsToContents()
        self.roiTable.horizontalHeader().setStretchLastSection(True)
        self.roiTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        sideMenuLayout = QVBoxLayout()
        sideMenuLayout.addWidget(QLabel("ROI Points"))
        sideMenuLayout.addWidget(self.roiTable)
        sideMenuLayout.addWidget(sideMenuBottom)

        sideMenu.setLayout(sideMenuLayout)

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(contentLayout)
        mainLayout.addWidget(sideMenu)

        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)

        # Processing Function
        self.tracking = ManualTracking()
        self.tracking.roiUpdated.connect(self.roiUpdated)
        self.thread = QThread()
        self.tracking.moveToThread(self.thread)
        self.tracking.finished.connect(self.videoLoaded)
        self.tracking.openVideoProgress.connect(self.videoProgress)

        self.thread.started.connect(self.tracking.getVideo)
        self.setCentralWidget(mainWidget)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Left:
            self.sliderMinusClicked()
        if event.key() == Qt.Key.Key_Right:
            self.sliderPlusClicked()

    def roiUpdated(self):
        points = self.tracking.getRoiPoints()
        self.roiTable.setRowCount(len(points))
        row = 0
        for point in points:
            self.roiTable.setItem(row, 0, QTableWidgetItem(str(point.index())))
            self.roiTable.setItem(row, 1, QTableWidgetItem(str(point.x())))
            self.roiTable.setItem(row, 2, QTableWidgetItem(str(point.y())))
            row += 1

    def mainVideoViewMousePressEvent(self, event: QMouseEvent):
        if not self.tracking.isLoaded():
            return
        maxWidth = self.scaledPixmap.width()
        maxHeight = self.scaledPixmap.height()
        point = event.pos()
        if point.x() < maxWidth and point.y() < maxHeight:
            self.tracking.setCurrentFrameROI(point.x(), point.y())
            self.updateVideoPreview()

    def resizeEvent(self, event):
        if not self.tracking.isLoaded():
            return
        self.updateVideoPreview()

    def onExitClicked(self, s):
        self.close()

    def exportData(self):
        if not self.tracking.isLoaded():
            return
        dirname = QFileDialog.getExistingDirectory(self, "Select Directory")
        if len(dirname) > 0 and not self.tracking.isSaving():
            self.sliderStatus.setText("Saving file")
            self.tracking.setDirname(dirname)
            self.tracking.saveData()
            self.sliderStatus.setText("Save complete")

    def onFileOpen(self, s):
        filename = QFileDialog.getOpenFileName(
            self, "Open file", "~/", "Video files (*.mp4 *.avi)"
        )
        loadingText = "Loading Video..."
        if len(filename[0]) > 0 and (self.sliderStatus.text() != loadingText):
            self.sliderStatus.setText(loadingText)
            self.tracking.setFilename(filename[0])
            self.thread.start()

    def videoProgress(self, update: str):
        self.sliderStatus.setText(update)

    def videoLoaded(self):
        self.sliderWidget.setValue(1)
        self.sliderWidget.setMinimum(1)
        self.sliderWidget.setMaximum(self.tracking.getTotalFrame())

        self.tracking.setCurrentFrame(0)
        self.updateVideoPreview()

        self.sliderStatus.setText("Video Loaded")

    def sliderMinusClicked(self):
        if self.sliderWidget.value() > 1:
            self.sliderWidget.setValue(self.sliderWidget.value() - 1)

    def sliderPlusClicked(self):
        if self.sliderWidget.value() < self.sliderWidget.maximum():
            self.sliderWidget.setValue(self.sliderWidget.value() + 1)

    def sliderChanged(self, value):
        if not self.tracking.isLoaded():
            return
        self.tracking.setCurrentFrame(value - 1)
        self.updateVideoPreview()
        self.sliderStatus.setText("Viewing frame {}".format(value))

    def updateVideoPreview(self):
        frame = self.tracking.getFrame()
        pixmap = QPixmap(frame)
        w = self.mainVideoView.width()
        h = self.mainVideoView.height()
        self.scaledPixmap = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio)
        scale = self.scaledPixmap.height() / frame.height()
        self.tracking.setScale(scale)
        self.mainVideoView.setPixmap(self.scaledPixmap)


app = QApplication(sys.argv)
w = MainWindow()
w.show()
w.resize(800, 600)
w.showMaximized()
app.exec()

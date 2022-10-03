from math import floor
import cv2 as cv
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage

import csv
import os
from PIL import Image


class Point:
    __index: int
    __x: int
    __y: int

    def __init__(self, x: int, y: int):
        self.__x = x
        self.__y = y

    def setIndex(self, index: int):
        self.__index = index

    def index(self):
        return self.__index

    def x(self):
        return self.__x

    def y(self):
        return self.__y


class ManualTracking(QObject):
    __filename: str
    __dirname: str

    __frames: list[np.ndarray]
    __videoWidth: int
    __videoHeight: int
    __scale: float
    __videoFPS: int
    __currentFrame: int
    __roiPoints: np.ndarray

    __videoLoaded: bool
    __saving: bool

    __roiSize: int

    roiUpdated = pyqtSignal()
    finished = pyqtSignal()
    openVideoProgress = pyqtSignal(str)
    saveDataProgress = pyqtSignal(str)

    def __init__(self):
        super(ManualTracking, self).__init__()
        self.__frames = []
        self.__videoLoaded = False
        self.__saving = False
        self.__roiSize = 50
        return

    def setFilename(self, filename: str):
        self.__filename = filename

    def setDirname(self, direname: str):
        self.__dirname = direname

    def getRoiPoints(self) -> list[Point]:
        points = []
        index = 0
        for point in self.__roiPoints:
            if point is not None:
                point.setIndex(index)
                points.append(point)
            index += 1
        return points

    def getVideo(self):
        if self.__filename:
            self.__videoLoaded = False
            self.__frames.clear()
            cap = cv.VideoCapture(self.__filename)
            self.__videoFPS = int(cap.get(cv.CAP_PROP_FPS))
            self.__videoWidth = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
            self.__videoHeight = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
            totalFrames = cap.get(cv.CAP_PROP_FRAME_COUNT)
            currentFrame = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if ret == True:
                    currentFrame += 1
                    self.__frames.append(frame)
                    self.openVideoProgress.emit(
                        "Reading {}, progress: {:.2f}%".format(
                            self.__filename, currentFrame / totalFrames * 100
                        )
                    )
                else:
                    break
            self.__roiPoints = np.empty(currentFrame, dtype=object)
            self.__videoLoaded = True
            self.finished.emit()

    def setScale(self, scale: float):
        self.__scale = scale

    def setCurrentFrame(self, index: int):
        if not self.__videoLoaded:
            return
        self.__currentFrame = index

    def saveData(self):
        if not self.__videoLoaded:
            return
        with open(os.path.join(self.__dirname, "data.csv"), "w") as csvfile:
            writer = csv.writer(csvfile)
            for point in self.__roiPoints:
                if point is not None:
                    writer.writerow([point.index(), point.x(), point.y()])
                    frame = self.__frames[point.index()]
                    im = Image.fromarray(frame)

                    dStart = floor(self.__roiSize / 2)
                    dEnd = self.__roiSize - dStart
                    left = point.x() - dStart
                    top = point.y() - dStart
                    right = point.x() + dEnd
                    bottom = point.y() + dEnd

                    im1 = im.crop((left, top, right, bottom))
                    im1.save(
                        os.path.join(
                            self.__dirname, str(point.index()).zfill(5) + ".png"
                        )
                    )
            self.saveDataProgress.emit("Roi points saved")

    def getFrame(self):
        if not self.__videoLoaded:
            return

        # Get Frame
        current = self.__currentFrame
        frame = self.__frames[current].copy()

        point = self.__roiPoints[current]

        if point is not None:
            dStart = floor(self.__roiSize / 2)
            dEnd = self.__roiSize - dStart
            start_point = (point.x() - dStart, point.y() - dStart)
            end_point = (point.x() + dEnd, point.y() + dEnd)
            color = (255, 0, 0)
            thickness = 2
            cv.rectangle(frame, start_point, end_point, color, thickness)

        bytesPerLine = 3 * self.__videoWidth
        return QImage(
            frame,
            self.__videoWidth,
            self.__videoHeight,
            bytesPerLine,
            QImage.Format.Format_RGB888,
        )

    def getTotalFrame(self):
        return len(self.__frames)

    def setCurrentFrameROI(self, x: int, y: int):
        if not self.__videoLoaded:
            return
        self.__roiPoints[self.__currentFrame] = Point(
            round(x / self.__scale), round(y / self.__scale)
        )
        self.roiUpdated.emit()

    def isLoaded(self):
        return self.__videoLoaded

    def isSaving(self):
        return self.__saving

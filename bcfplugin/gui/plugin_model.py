import os
import copy

from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import (QAbstractListModel, QModelIndex, Slot, Signal, Qt,
        QSize)

import bcfplugin.programmaticInterface as pI
import bcfplugin.util as util

from uuid import uuid4
from bcfplugin.rdwr.topic import Topic
from bcfplugin.rdwr.markup import Comment


def openProjectBtnHandler(file):

    """ Handler of the "Open" button for a project """

    pI.openProject(file)


def getProjectName():

    """ Wrapper for programmaticInterface.getProjectName() """

    return pI.getProjectName()


def saveProject(dstFile):

    """ Wrapper for programmaticInterface.saveProject() """

    pI.saveProject(dstFile)


class TopicCBModel(QAbstractListModel):

    selectionChanged = Signal((Topic,))

    def __init__(self):
        QAbstractListModel.__init__(self)
        self.updateTopics()
        self.items = []


    def updateTopics(self):

        self.beginResetModel()

        if not pI.isProjectOpen():
            self.endResetModel()
            return

        topics = pI.getTopics()
        if topics != pI.OperationResults.FAILURE:
            self.items = [ topic[1] for topic in topics ]

        self.endResetModel()


    def rowCount(self, parent = QModelIndex()):
        return len(self.items) + 1 # plus the dummy element


    def data(self, index, role = Qt.DisplayRole):

        idx = index.row()
        if role == Qt.DisplayRole:
            if idx == 0:
                return "-- Select your topic --"
            return self.items[idx - 1].title # subtract the dummy element

        else:
            return None


    def flags(self, index):
        flaggs = Qt.ItemIsEnabled
        if index.row() != 0:
            flaggs |= Qt.ItemIsSelectable
        return flaggs


    @Slot(int)
    def newSelection(self, index):

        if index > 0: # 0 is the dummy element
            self.selectionChanged.emit(self.items[index - 1])


    @Slot()
    def projectOpened(self):
        self.updateTopics()


class CommentModel(QAbstractListModel):

    def __init__(self, parent = None):

        QAbstractListModel.__init__(self, parent)
        self.items = []
        self.currentTopic = None


    @Slot(Topic)
    def resetItems(self, topic = None):

        """ Load comments from `topic`.

        If topic is set to `None` then all elements will be deleted from the
        model."""

        self.beginResetModel()

        if topic is None:
            del self.items
            self.items = list()
            self.endResetModel()
            return

        if not pI.isProjectOpen():
            util.showError("First you have to open a project.")
            util.printError("First you have to open a project.")
            self.endResetModel()
            return

        comments = pI.getComments(topic)
        if comments == pI.OperationResults.FAILURE:
            util.showError("Could not get any comments for topic" \
                    " {}".format(str(topic)))
            util.printError("Could not get any comments for topic" \
                    " {}".format(str(topic)))
            self.endResetModel()
            return

        self.items = [ comment[1] for comment in comments ]
        self.currentTopic = topic

        self.endResetModel()


    def removeRow(self, index):

        if not index.isValid():
            return False

        self.beginRemoveRows(index, index.row(), index.row())
        idx = index.row()
        commentToRemove = self.items[idx]
        result = pI.deleteObject(commentToRemove)
        if result == pI.OperationResults.FAILURE:
            return False

        self.items.pop(idx)
        self.endRemoveRows()

        # load comments of the topic anew
        self.resetItems(self.currentTopic)
        return True


    def rowCount(self, parent = QModelIndex()):

        return len(self.items)


    def data(self, index, role=Qt.DisplayRole):

        if not index.isValid() or (role != Qt.DisplayRole and
                role != Qt.EditRole and role != Qt.ForegroundRole):
            return None

        comment = None
        item = self.items[index.row()]
        commentText = ""
        commentAuthor = ""
        commentDate = ""
        dateFormat = "%Y-%m-%d %X"
        if role == Qt.DisplayRole:
            commentText = item.comment
            commentAuthor = item.author if item.modAuthor == "" else item.modAuthor
            commentDate = (item.date if item.modDate == item._modDate.defaultValue else item.modDate)
            commentDate = commentDate.strftime(dateFormat)
            comment = (commentText, commentAuthor, commentDate)

        elif role == Qt.EditRole: # date is automatically set when editing
            commentText = item.comment
            commentAuthor = item.author if item.modAuthor == "" else item.modAuthor
            comment = (commentText, commentAuthor)

        elif role == Qt.ForegroundRole:
            # set the color if a viewpoint is linked to the comment
            white = QColor("black")
            vpCol = QColor("blue")
            col = white if item.viewpoint is None else vpCol
            brush = QBrush()
            brush.setColor(col)

            return brush

        return comment


    def flags(self, index):

        fl = Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled
        return fl


    def checkValue(self, text):

        splitText = [ textItem.strip() for textItem in text.split("--") ]
        if len(splitText) != 2:
            return None

        return splitText


    def setData(self, index, value, role=Qt.EditRole):
        # https://doc.qt.io/qtforpython/PySide2/QtCore/QAbstractItemModel.html#PySide2.QtCore.PySide2.QtCore.QAbstractItemModel.roleNames

        if not index.isValid() or role != Qt.EditRole:
            return False

        splitText = self.checkValue(value)
        if not splitText:
            return False

        commentToEdit = self.items[index.row()]
        commentToEdit.comment = splitText[0]
        commentToEdit.modAuthor = splitText[1]

        pI.modifyElement(commentToEdit, splitText[1])
        topic = pI.getTopic(commentToEdit)
        self.resetItems(topic)

        return True


    def addComment(self, value):

        """ Add a new comment to the items list.

        For the addition the programmatic Interface is used. It creates a unique
        UUID for the comment, as well as it takes the current time stamp
        """

        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        splitText = self.checkValue(value)
        if not splitText:
            self.endInsertRows()
            return False

        success = pI.addComment(self.currentTopic, splitText[0], splitText[1], None)
        if success == pI.OperationResults.FAILURE:
            self.endInsertRows()
            return False

        self.endInsertRows()
        # load comments anew
        self.resetItems(self.currentTopic)

        return True


class SnapshotModel(QAbstractListModel):


    def __init__(self, parent = None):

        QAbstractListModel.__init__(self, parent)
        # Size of an icon
        self.size = QSize(100, 100)
        # currently open topic
        self.currentTopic = None
        # list of the snapshot files
        self.snapshotList = []
        # buffer of the already loaded images
        self.snapshotImgs = []


    def data(self, index, role = Qt.DisplayRole):

        if not index.isValid():
            return None

        # only return icons.
        if not role == Qt.DecorationRole:
            return None

        # lazy loading images into `self.snapshotImgs`
        if self.snapshotImgs[index.row()] is None:
            img = self.loadImage(self.snapshotList[index.row()])
            self.snapshotImgs[index.row()] = img

        img = self.snapshotImgs[index.row()]
        if img is None: # happens if the image could not be loaded
            return None

        # scale image to currently set size
        img = img.scaled(self.size, Qt.KeepAspectRatio)
        return img


    def rowCount(self, parent = QModelIndex()):

        # only show the first three snapshots.
        return len(self.snapshotList) if len(self.snapshotList) < 3 else 3


    def imgFromFilename(self, filename):

        """ Returns the image with `filename`. It is loaded if it isn't at the
        point of inquiry.

        The image is returned in original resolution. The user is responsible
        for scaling it to the desired size.
        """

        filenameList = [ os.path.basename(path) for path in self.snapshotList ]
        if filename not in filenameList:
            return None

        idx = filenameList.index(filename)
        if self.snapshotImgs[idx] is None:
            img = self.loadImage(self.snapshotList[idx])
            self.snapshotImgs[idx] = img

        img = self.snapshotImgs[idx]
        if img is None: # image could not be loaded (FileNotFoundError?)
            return None

        return img


    def realImage(self, index):

        """ Return the image at `index` in original resolution """

        if not index.isValid():
            return None

        if self.snapshotImgs[index.row()] is None:
            return None

        img = self.snapshotImgs[index.row()]
        return img


    def loadImage(self, path):

        """ Load the image behind `path` and return a QPixmap """

        if not os.path.exists(path):
            QMessageBox.information(None, tr("Image Load"), tr("The image {}"\
                    " could not be found.".format(path)),
                    QMessageBox.Ok)
            return None

        imgReader = QImageReader(path)
        imgReader.setAutoTransform(True)
        img = imgReader.read()
        if img.isNull():
            QMessageBox.information(None, tr("Image Load"), tr("The image {}"\
                    " could not be loaded. Skipping it then.".format(path)),
                    QMessageBox.Ok)
            return None

        return QPixmap.fromImage(img)


    def setSize(self, newSize: QSize):

        """ Sets the size in which the Pixmaps are returned """

        self.size = newSize


    @Slot()
    def resetItems(self, topic = None):

        """ Reset the internal state of the model.

        If `topic` != None then the snapshots associated with the new topic are
        loaded, else the list of snapshots is cleared.
        """

        self.beginResetModel()

        self.currentTopic = topic
        snapshots = pI.getSnapshots(self.currentTopic)
        if snapshots == pI.OperationResults.FAILURE:
            self.snapshotList = []
        else:
            self.snapshotList = snapshots

        # clear the image buffer
        self.snapshotImgs = [None]*len(snapshots)
        self.endResetModel()


class ViewpointsListModel(QAbstractListModel):

    """
    Model class to the viewpoins list.

    It returns the name of a viewpoint, associated with the current topic as
    well as an icon of the snapshot file that is referenced in the viewpoint. If
    no snapshot is referenced then no icon is returned.  An icon is 10x10
    millimeters in dimension. The actual sizes and offsets, in pixels, are
    stored in variables containing 'Q'. All other sizes and offset variables
    hold values in millimeters.These sizes and offsets are scaled to the
    currently active screen, retrieved by `util.getCurrentQScreen()`.
    """

    def __init__(self, snapshotModel, parent = None):

        QAbstractListModel.__init__(self, parent = None)
        # holds instances of ViewpointReference
        self.viewpoints = []
        # used to retrieve the snapshot icons.
        self.snapshotModel = snapshotModel

        # set up the sizes and offsets
        self._iconQSize = None # size in pixels
        self._iconSize = QSize(10, 10) # size in millimeters
        self.calcSizes()


    @Slot()
    def calcSizes(self):

        """ Convert the millimeter sizes/offsets into pixels depending on the
        current screen. """

        screen = util.getCurrentQScreen()
        # pixels per millimeter (not parts per million)
        ppm = screen.logicalDotsPerInch() / util.MMPI

        width = self._iconSize.width() * ppm
        height = self._iconSize.height() * ppm
        self._iconQSize = QSize(width, height)


    @Slot()
    def resetItems(self, topic = None):

        """ If `topic != None` load viewpoints associated with `topic`, else
        delete the internal state of the model """

        self.beginResetModel()

        if topic is None:
            self.viewpoints = []
        else:
            self.viewpoints = [ vp[1] for vp in pI.getViewpoints(topic, False) ]

        self.endResetModel()


    def data(self, index, role = Qt.DisplayRole):

        if not index.isValid():
            return None

        viewpoint = self.viewpoints[index.row()]
        if role == Qt.DisplayRole:
            # return the name of the viewpoints file
            return str(viewpoint.file) + " (" + str(viewpoint.id) + ")"

        elif role == Qt.DecorationRole:
            # if a snapshot is linked, return an icon of it.
            filename = str(viewpoint.snapshot)
            icon = self.snapshotModel.imgFromFilename(filename)
            if icon is None: # snapshot is not listed in markup and cannot be loaded
                return None

            scaledIcon = icon.scaled(self._iconQSize, Qt.KeepAspectRatio)
            return scaledIcon


    def rowCount(self, parent = QModelIndex()):

        return len(self.viewpoints)


    def setIconSize(self, size: QSize):

        """ Size is expected to be given in millimeters. """

        self._iconSize = size
        self.calcSizes()



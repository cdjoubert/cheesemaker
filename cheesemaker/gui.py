# Authors: David Whitlock <alovedalongthe@gmail.com>
# A minimalistic image viewer
# Copyright (C) 2013-2014 David Whitlock
#
# Cheesemaker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cheesemaker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cheesemaker.  If not, see <http://www.gnu.org/licenses/gpl.html>.

from PyQt5.QtCore import *
from PyQt5.QtGui import QImage, QPixmap, QTransform, QPainter, QIcon, QCursor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem,
        QMenu, QDialog, QFileDialog, QAction, QMessageBox, QFrame, QRubberBand, qApp)
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtCore import pyqtRemoveInputHook
import pdb
from gi.repository import GExiv2
from functools import partial
import os
import sys
import random
import preferences, editimage
import argparse

# For debug, could be erased after
def trace(cond=True):
    pdb_obj = pdb.Pdb()
    if cond:
        pyqtRemoveInputHook()
        pdb_obj.set_trace(sys._getframe(1))


class MainWindow(QMainWindow):
    def __init__(self, parent):
        QMainWindow.__init__(self)

        self.printer = QPrinter()
        self.load_img = self.load_img_fit
        self.reload_img = self.reload_auto
        self.open_new = parent.open_win
        self.scene = QGraphicsScene()
        self.img_view = ImageView(self)
        self.img_view.setScene(self.scene)
        self.setCentralWidget(self.img_view)
        
        self.create_actions()
        self.create_menu()
        self.create_dict()
        self.create_toolbar()
        self.slides_next = True

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)

        self.read_prefs()
        self.read_list = parent.read_list
        self.write_list = parent.write_list
        self.pics_dir = os.path.expanduser('~/Pictures') or QDir.currentPath()
        self.resize(700, 500)

    def create_actions(self):
        self.open_act = QAction('&Open', self, shortcut='Ctrl+O')
        self.open_act.triggered.connect(self.open)
        self.open_new_act = QAction('Open new window', self, shortcut='Ctrl+Shift+O')
        self.open_new_act.triggered.connect(partial(self.open, True))
        self.reload_act = QAction('&Reload image', self, shortcut='Ctrl+R')
        self.reload_act.triggered.connect(self.reload_img)
        self.print_act = QAction('&Print', self, shortcut='Ctrl+P')
        self.print_act.triggered.connect(self.print_img)
        self.save_act = QAction('&Save image', self, shortcut='Ctrl+S')
        self.save_act.triggered.connect(self.save_img_as)
        self.close_act = QAction('Close window', self, shortcut='Ctrl+W')
        self.close_act.triggered.connect(self.close)
        self.exit_act = QAction('E&xit', self, shortcut='Ctrl+Q')
        self.exit_act.triggered.connect(self.exit)
        self.fulls_act = QAction('Fullscreen', self, shortcut='F11', checkable=True)
        self.fulls_act.triggered.connect(self.toggle_fs)
        self.ss_act = QAction('Slideshow', self, shortcut='F5', checkable=True)
        self.ss_act.triggered.connect(self.toggle_slideshow)
        self.ss_next_act = QAction('Next / Random image', self, checkable=True)
        self.ss_next_act.triggered.connect(self.set_slide_type)
        self.ss_next_act.setChecked(True)
        self.next_act = QAction('Next image', self, shortcut='Right')
        self.next_act.triggered.connect(self.go_next_img)
        self.prev_act = QAction('Previous image', self, shortcut='Left')
        self.prev_act.triggered.connect(self.go_prev_img)
        self.rotleft_act = QAction('Rotate left', self, shortcut='Ctrl+Left')
        self.rotleft_act.triggered.connect(partial(self.img_rotate, 270))
        self.rotright_act = QAction('Rotate right', self, shortcut='Ctrl+Right')
        self.rotright_act.triggered.connect(partial(self.img_rotate, 90))
        self.fliph_act = QAction('Flip image horizontally', self, shortcut='Ctrl+H')
        self.fliph_act.triggered.connect(partial(self.img_flip, -1, 1))
        self.flipv_act = QAction('Flip image vertically', self, shortcut='Ctrl+V')
        self.flipv_act.triggered.connect(partial(self.img_flip, 1, -1))
        self.resize_act = QAction('Resize image', self, triggered=self.resize_img)
        self.crop_act = QAction('Crop image', self, triggered=self.crop_img)
        self.zin_act = QAction('Zoom &In', self, shortcut='Up')
        self.zin_act.triggered.connect(partial(self.img_view.zoom, 1.1))
        self.zout_act = QAction('Zoom &Out', self, shortcut='Down')
        self.zout_act.triggered.connect(partial(self.img_view.zoom, 1 / 1.1))
        self.fit_win_act = QAction('Best &fit', self, checkable=True, shortcut='F',
                triggered=self.zoom_default)
        self.fit_win_act.setChecked(True)
        self.prefs_act = QAction('Preferences', self, triggered=self.set_prefs)
        self.props_act = QAction('Properties', self, triggered=self.get_props)
        self.help_act = QAction('&Help', self, shortcut='F1', triggered=self.help_page)
        self.about_act = QAction('&About', self, triggered=self.about_cm)
        self.aboutQt_act = QAction('About &Qt', self,
                triggered=qApp.aboutQt)

    def create_menu(self):
        self.popup = QMenu(self)
        main_acts = [self.open_act, self.open_new_act, self.reload_act, self.print_act, self.save_act]
        edit_acts1 = [self.rotleft_act, self.rotright_act, self.fliph_act, self.flipv_act]
        edit_acts2 = [self.resize_act, self.crop_act]
        view_acts = [self.next_act, self.prev_act, self.zin_act, self.zout_act, self.fit_win_act, self.fulls_act, self.ss_act, self.ss_next_act]
        help_acts = [self.help_act, self.about_act, self.aboutQt_act]
        end_acts = [self.prefs_act, self.props_act, self.close_act, self.exit_act]
        for act in main_acts:
            self.popup.addAction(act)
        edit_menu = QMenu(self.popup)
        edit_menu.setTitle('&Edit')
        for act in edit_acts1:
            edit_menu.addAction(act)
        edit_menu.addSeparator()
        for act in edit_acts2:
            edit_menu.addAction(act)
        self.popup.addMenu(edit_menu)
        view_menu = QMenu(self.popup)
        view_menu.setTitle('&View')
        for act in view_acts:
            view_menu.addAction(act)
        self.popup.addMenu(view_menu)
        help_menu = QMenu(self.popup)
        help_menu.setTitle('&Help')
        for act in help_acts:
            help_menu.addAction(act)
        self.popup.addMenu(help_menu)
        for act in end_acts:
            self.popup.addAction(act)

        self.action_list = main_acts + edit_acts1 + edit_acts2 + view_acts + help_acts + end_acts
        for act in self.action_list:
            self.addAction(act)

    def showMenu(self, pos):
        self.popup.popup(self.mapToGlobal(pos))
 
    def create_dict(self):
        """Create a dictionary to handle auto-orientation."""
        self.orient_dict = {None: self.load_img,
                '1': self.load_img,
                '2': partial(self.img_flip, -1, 1),
                '3': partial(self.img_rotate, 180),
                '4': partial(self.img_flip, -1, 1),
                '5': self.img_rotate_fliph,
                '6': partial(self.img_rotate, 90),
                '7': self.img_rotate_flipv,
                '8': partial(self.img_rotate, 270)}

    def create_toolbar(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        def icon(icon_name):
            return QIcon(os.path.join(script_dir, "assets", icon_name))
        
        def add_action(description, icon_file, function):
            action = QAction(icon(icon_file), description, self)
            action.triggered.connect(function)
            self.toolbar.addAction(action)
        
        self.toolbar = self.addToolBar("File")
        add_action("save", "save.png", self.save_img)
        add_action("crop", "crop.png", self.crop_img)
        add_action("resize", "resize.png", self.resize_img)
        add_action("save important", "star.png", lambda : self.save_img(rating=100))
        add_action("save non important", "hollow_star.png", lambda : self.save_img(rating=0))


    def read_prefs(self):
        """Parse the preferences from the config file, or set default values."""
        try:
            conf = preferences.Config()
            values = conf.read_config()
            self.auto_orient = values[0]
            self.slide_delay = values[1]
            self.quality = values[2]
        except:
            self.auto_orient = True
            self.slide_delay = 5
            self.quality = 90
        self.reload_img = self.reload_auto if self.auto_orient else self.reload_nonauto

    def set_prefs(self):
        """Write preferences to the config file."""
        dialog = preferences.PrefsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.auto_orient = dialog.auto_orient
            self.slide_delay = dialog.delay_spinb.value()
            self.quality = dialog.qual_spinb.value()
            conf = preferences.Config()
            conf.write_config(self.auto_orient, self.slide_delay, self.quality)
        self.reload_img = self.reload_auto if self.auto_orient else self.reload_nonauto

    def open(self, new_win=False):
        fname = QFileDialog.getOpenFileName(self, 'Open File', self.pics_dir)[0]
        if fname:
            if fname.lower().endswith(self.read_list):
                if new_win:
                    self.open_new(fname)
                else:
                    self.open_img(fname)
            else:
                QMessageBox.information(self, 'Error', 'Cannot load {} images.'.format(fname.rsplit('.', 1)[1]))

    def open_img(self, fname):
        self.fname = fname
        self.reload_img()
        dirname = os.path.dirname(self.fname)
        self.set_img_list(dirname)
        self.img_index = self.filelist.index(self.fname)

    def set_img_list(self, dirname):
        """Create a list of readable images from the current directory."""
        filelist = os.listdir(dirname)
        self.filelist = [os.path.join(dirname, fname) for fname in filelist
                        if fname.lower().endswith(self.read_list)]
        self.filelist.sort()
        self.last_file = len(self.filelist) - 1

    def set_title(self):
        file_name = self.fname.rsplit('/', 1)[1]
        size = " [%d x %d]" % (self.pixmap.width(), self.pixmap.height())
        self.setWindowTitle(file_name + size)

    def get_img(self):
        """Get image from fname and create pixmap."""
        image = QImage(self.fname)
        self.pixmap = QPixmap.fromImage(image)

    def reload_auto(self):
        """Load a new image with auto-orientation."""
        self.get_img()
        try:
            orient = GExiv2.Metadata(self.fname)['Exif.Image.Orientation']
            self.orient_dict[orient]()
        except:
            self.load_img()

    def reload_nonauto(self):
        """Load a new image without auto-orientation."""
        self.get_img()
        self.load_img()

    def load_img_fit(self):
        """Load the image to fit the window."""
        self.scene.clear()
        self.scene.addPixmap(self.pixmap)
        self.scene.setSceneRect(0, 0, self.pixmap.width(), self.pixmap.height())
        self.img_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.set_title()

    def load_img_1to1(self):
        """Load the image at its original size."""
        self.scene.clear()
        self.img_view.resetTransform()
        self.scene.addPixmap(self.pixmap)
        self.scene.setSceneRect(0, 0, self.pixmap.width(), self.pixmap.height())
        pixitem = QGraphicsPixmapItem(self.pixmap)
        self.img_view.centerOn(pixitem)
        self.set_title()

    def go_next_img(self):
        self.img_index = self.img_index + 1 if self.img_index < self.last_file else 0
        self.fname = self.filelist[self.img_index]
        self.reload_img()

    def go_prev_img(self):
        self.img_index = self.img_index - 1 if self.img_index else self.last_file
        self.fname = self.filelist[self.img_index]
        self.reload_img()

    def zoom_default(self):
        """Toggle best fit / original size loading."""
        if self.fit_win_act.isChecked():
            self.load_img = self.load_img_fit
            self.create_dict()
            self.load_img()
        else:
            self.load_img = self.load_img_1to1
            self.create_dict()
            self.load_img()

    def img_rotate(self, angle):
        self.pixmap = self.pixmap.transformed(QTransform().rotate(angle))
        self.load_img()

    def img_flip(self, x, y):
        self.pixmap = self.pixmap.transformed(QTransform().scale(x, y))
        self.load_img()

    def img_rotate_fliph(self):
        self.img_rotate(90)
        self.img_flip(-1, 1)

    def img_rotate_flipv(self):
        self.img_rotate(90)
        self.img_flip(1, -1)

    def resize_img(self):
        dialog = editimage.ResizeDialog(self, self.pixmap.width(), self.pixmap.height())
        if dialog.exec_() == QDialog.Accepted:
            width = dialog.get_width.value()
            height = dialog.get_height.value()
            self.pixmap = self.pixmap.scaled(width, height, Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation)
            self.load_img()
    
    def crop_img(self):
        def callback(coords):
            self.pixmap = self.pixmap.copy(*coords)
            self.load_img()
        self.img_view.crop(callback)

    def toggle_fs(self):
        if self.fulls_act.isChecked():
            self.showFullScreen()
        else:
            self.showNormal()

    def toggle_slideshow(self):
        if self.ss_act.isChecked():
            self.showFullScreen()
            self.start_ss()
        else:
            self.toggle_fs()
            self.timer.stop()
            self.ss_timer.stop()

    def start_ss(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_img)
        self.timer.start(self.slide_delay * 1000)
        self.ss_timer = QTimer()
        self.ss_timer.timeout.connect(self.update_img)
        self.ss_timer.start(60000)

    def update_img(self):
        if self.slides_next:
            self.go_next_img()
        else:
            self.fname = random.choice(self.filelist)
            self.reload_img()

    def set_slide_type(self):
        self.slides_next = self.ss_next_act.isChecked()

    def save_img_as(self):
        fname = QFileDialog.getSaveFileName(self, 'Save your image', self.fname)[0]
        if fname:
            if fname.lower().endswith(self.write_list):
                keep_exif = QMessageBox.question(self, 'Save exif data',
                        'Do you want to save the picture metadata?', QMessageBox.Yes |
                        QMessageBox.No, QMessageBox.Yes)
                if keep_exif == QMessageBox.Yes:
                    exif = GExiv2.Metadata(self.fname)
                    self.pixmap.save(fname, None, self.quality)
                    if exif:
                        saved_exif = GExiv2.Metadata(fname)
                        for tag in exif.get_exif_tags():
                            saved_exif[tag] = exif[tag]
                        saved_exif.set_orientation(GExiv2.Orientation.NORMAL)
                        saved_exif.save_file()
            else:
                QMessageBox.information(self, 'Error', 'Cannot save {} images.'.format(fname.rsplit('.', 1)[1]))

    def save_img(self, rating=None):
        exif = GExiv2.Metadata(self.fname)
        self.pixmap.save(self.fname, None, self.quality)
        if rating is not None:
            exif["Exif.Image.Rating"] = str(rating)
        if exif:
            exif.save_file()

    def print_img(self):
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_():
            painter = QPainter(self.printer)
            rect = painter.viewport()
            if self.pixmap.width() > self.pixmap.height():
                self.pixmap = self.pixmap.transformed(QTransform().rotate(90))
            size = self.pixmap.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.pixmap.rect())
            painter.drawPixmap(0, 0, self.pixmap)

    def resizeEvent(self, event=None):
        if self.fit_win_act.isChecked():
            try:
                self.load_img()
            except:
                pass

    def get_props(self):
        """Get the properties of the current image."""
        image = QImage(self.fname)
        preferences.PropsDialog(self, self.fname.rsplit('/', 1)[1], image.width(), image.height())

    def help_page(self):
        preferences.HelpDialog(self)

    def about_cm(self):
        about_message = 'Version: 0.3.9\nAuthor: David Whitlock\nLicense: GPLv3'
        QMessageBox.about(self, 'About Cheesemaker', about_message)


    def exit(self):
        QCoreApplication.quit()

class ImageView(QGraphicsView):
    @staticmethod
    def close_enough(point1, point2):
        d = 20
        return abs(point1.x() - point2.x()) < d and abs(point1.y() - point2.y()) < d
        
    def __init__(self, parent=None):
        QGraphicsView.__init__(self, parent)

        self.go_prev_img = parent.go_prev_img
        self.go_next_img = parent.go_next_img

        pal = self.palette()
        pal.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(pal)
        self.setFrameShape(QFrame.NoFrame)
        
        self.rband = None
        self.rband_state = None
        self.rband_corner = None # If mouse is over a corner
        self.rband_origin = QPoint()
        self.rband_endpoint = QPoint()

    def mousePressEvent(self, event):
        """Go to the next / previous image, or be able to drag the image with a hand."""
        if self.rband_state == "initial":
            self.rband = QRubberBand(QRubberBand.Rectangle, self)
            self.rband_origin = event.pos()
            self.rband.setGeometry(QRect(self.rband_origin, QSize()))
            self.rband.show()
            self.rband_state = "set-endpoint"
        elif self.rband_state == "drawn":
            if self.rband_corner == "nw":
                self.rband_state = "set-origin"
            elif self.rband_corner == "se":
                self.rband_state = "set-endpoint"
            elif self.rband_corner == "inside":
                self.rband_state = "move"
                self.setCursor(QCursor(Qt.ClosedHandCursor))
                self.rband_previous_pos = event.pos()
        else:
            if event.button() == Qt.LeftButton:
                x = event.x()
                if x < 100:
                    self.go_prev_img()
                elif x > self.width() - 100:
                    self.go_next_img()
                else:
                    self.setDragMode(QGraphicsView.ScrollHandDrag)
        QGraphicsView.mousePressEvent(self, event)
    
    def mouseMoveEvent(self, event):
        if self.rband_state == "set-endpoint":
            self.rband.setGeometry(QRect(self.rband_origin, event.pos()).normalized())
            self.rband_endpoint = event.pos()
        elif self.rband_state == "set-origin":
            self.rband.setGeometry(QRect(event.pos(), self.rband_endpoint).normalized())
            self.rband_origin = event.pos()
        elif self.rband_state == "move":
            old_pos = self.rband.geometry()
            new_pos = old_pos.translated(event.pos() - self.rband_previous_pos)
            trace(0)
            self.rband.setGeometry(new_pos)
            self.rband_previous_pos = event.pos()
        elif self.rband_state == "drawn":
            if ImageView.close_enough(self.rband_origin, event.pos()):
                self.rband_corner = "nw"
                self.setCursor(QCursor(Qt.SizeFDiagCursor))
            elif ImageView.close_enough(self.rband_endpoint, event.pos()):
                self.rband_corner = "se"
                self.setCursor(QCursor(Qt.SizeFDiagCursor))
            elif self.rband.geometry().contains(event.pos()):
                self.rband_corner = "inside"
                self.setCursor(QCursor(Qt.OpenHandCursor))
            else:
                self.rband_corner = None
                self.setCursor(QCursor(Qt.ArrowCursor))
        QGraphicsView.mouseMoveEvent(self, event)
            
    def mouseReleaseEvent(self, event):
        #print("State %s", self.rband_state)
        if self.rband_state == "set-endpoint" or self.rband_state == "set-origin":
            self.rband_state = "drawn"
        elif self.rband_state == "move":
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.rband_state = "drawn"
            self.rband_origin = self.rband.geometry().topLeft()
            self.rband_endpoint = self.rband.geometry().bottomRight()
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.setDragMode(QGraphicsView.NoDrag)
        QGraphicsView.mouseReleaseEvent(self, event)
    
    def keyPressEvent(self, event):
        if self.rband_state == "drawn":
            if event.key() == Qt.Key_Escape:
                self.setCursor(QCursor(Qt.ArrowCursor))
                self.rband.hide()
                self.rband_state = None
                self.setMouseTracking(False)
            elif event.key() in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space]:
                self.setCursor(QCursor(Qt.ArrowCursor))
                self.rband.hide()
                self.rband_state = None
                self.setMouseTracking(False)
                #print("CB ", self.get_coords())
                self.crop_callback(self.get_coords())
        event.accept()
        

    def zoom(self, zoomratio):
        self.scale(zoomratio, zoomratio)

    def wheelEvent(self, event):
        zoomratio = 1.1
        if event.angleDelta().y() < 0:
            zoomratio = 1.0 / zoomratio
        self.scale(zoomratio, zoomratio)

    def crop(self, callback):
        self.crop_callback = callback
        self.rband_state = "initial"
        self.setMouseTracking(True)

    def get_coords(self):
        rect = self.rband.geometry()
        size = self.mapToScene(rect).boundingRect()
        x = int(size.x())
        y = int(size.y())
        width = int(size.width())
        height = int(size.height())
        return (x, y, width, height)

class ImageViewer(QApplication):
    def __init__(self, qt_args, parsed_args):
        QApplication.__init__(self, qt_args)

        self.args = parsed_args
        self.read_list = ('bmp', 'gif', 'ico', 'jpg', 'jpeg', 'png', 'pbm',
                'pgm', 'ppm', 'xbm', 'xpm', 'svg', 'svgz', 'mng', 'wbmp',
                'tga', 'tif', 'tiff')
        self.write_list = ('bmp', 'ico', 'jpg', 'jpeg', 'pbm', 'pgm', 'png',
                'wbmp', 'tif', 'tiff', 'ppm', 'xbm', 'xpm')

    def startup(self):
        if len(self.args.files) > 0:
            self.open_files(self.args.files)
        else:
            self.open_win(None)

    def open_files(self, files):
        for fname in files:
            if fname.lower().endswith(self.read_list):
                self.open_win(fname)

    def open_win(self, fname):
        win = MainWindow(self)
        win.show()
        if fname:
            win.open_img(fname)
        else:
            win.open()

def main(qt_args, parsed_args):
    app = ImageViewer(qt_args, parsed_args)
    app.startup()
    sys.exit(app.exec_())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Image viewer")
    parser.add_argument('files', nargs='*', help='Open file or directory')

    # See: https://stackoverflow.com/a/21166631/2798802
    parsed_args, unparsed_args = parser.parse_known_args()
    qt_args = sys.argv[:1] + unparsed_args
    
    main(qt_args, parsed_args)

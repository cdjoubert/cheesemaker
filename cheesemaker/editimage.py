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

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QGridLayout, QLabel, QSpinBox, QCheckBox, QVBoxLayout, QPushButton

class SpinBox(QSpinBox):
    def __init__(self, val, maxval, step, func):
        QSpinBox.__init__(self)

        self.setRange(0, maxval)
        self.setValue(val)
        self.setSingleStep(step)
        self.valueChanged.connect(func)

class ButtonGrid(QGridLayout):
    def __init__(self, size_list, button_callback, parent=None):
        self.button_callback = button_callback
        self.push_buttons = []
        super().__init__(parent)
        self.addWidget(QLabel('Give size: '), 0, 0, 1, 2)
        self.addWidget(QLabel('Width'), 1, 0)
        self.addWidget(QLabel('Height'), 1, 1)
        self.row_col = [2, 0]
        for size in size_list:
            self.add_two_buttons(size)

    def add_one_button(self, label, *pargs):
        button = QPushButton(label)
        self.addWidget(button, self.row_col[0], self.row_col[1])
        self.row_col[1] += 1
        if self.row_col[1] >1:
            self.row_col[1] = 0
            self.row_col[0] += 1
        button.clicked.connect(lambda : self.button_callback(label, *pargs))
        return button
            
    def add_two_buttons(self, value):
        b = self.add_one_button("W = " + str(value), value, True)
        b = self.add_one_button("H = " + str(value), value, False)

class ResizeDialog(QDialog):
    def __init__(self, parent, width, height):
        QDialog.__init__(self, parent)

        self.setWindowTitle('Resize image')
        self.ratio = width / height
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.set_predefined_sizes(main_layout, [1600, 1200, 1000, 800, 640, 320, 200])
        self.set_resize_view(main_layout, width, height)
        self.set_aspratio_view(main_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.resize(250, 150)
        self.show()

    def set_predefined_sizes(self, main_layout, size_list):
        button_grid_layout = ButtonGrid(size_list, self.size_button_click)
        main_layout.addLayout(button_grid_layout)
    
    def set_height(self, value):
        self.get_height.blockSignals(True)
        self.get_height.setValue(value)
        self.get_height.blockSignals(False)

    def set_width(self, value):
        print("set_width ", value)
        self.get_width.blockSignals(True)
        self.get_width.setValue(value)
        self.get_width.blockSignals(False)

    def size_button_click(self, label, value, is_width):
        print("size_button_click ", label, value, is_width)
        if is_width:
            self.set_width(value)
            self.width_changed(value)
        else:
            self.set_height(value)
            self.height_changed(value)

    def set_resize_view(self, main_layout, width, height):
        grid_layout = QGridLayout()
        main_layout.addLayout(grid_layout)
        grid_layout.addWidget(QLabel('Width'), 0, 0, 1, 1)
        self.get_width = SpinBox(width, width, 10, self.width_changed)
        grid_layout.addWidget(self.get_width, 0, 1, 1, 1)

        grid_layout.addWidget(QLabel('Height'), 1, 0, 1, 1)
        self.get_height = SpinBox(height, height, 10, self.height_changed)
        grid_layout.addWidget(self.get_height, 1, 1, 1, 1)

    def set_aspratio_view(self, main_layout):
        self.pres_aspratio = True
        self.aspratio = QCheckBox('Preserve aspect ratio')
        self.aspratio.setChecked(True)
        self.aspratio.toggled.connect(self.toggle_aspratio)
        main_layout.addWidget(self.aspratio)

    def width_changed(self, value):
        if self.pres_aspratio:
            height = value / self.ratio
            self.set_height(height)

    def height_changed(self, value):
        if self.pres_aspratio:
            width = value * self.ratio
            self.set_width(width)

    def toggle_aspratio(self):
        """Toggle whether aspect ratio should be preserved."""
        self.pres_aspratio = self.aspratio.isChecked()

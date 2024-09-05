
import ismrmrd
import h5py

from PySide6 import QtWidgets
# from PySide6.QtCore import Qt
# from PySide6.QtGui import QGuiApplication, QCursor
import numpy as np
import os
import subprocess

class FileWidget(QtWidgets.QWidget):

    def __init__(self, parent, file_name):
        super().__init__(parent)

        self.file_name = file_name 
        self.tree = QtWidgets.QTreeWidget(self)
        self.tree.setColumnCount(2)
        # self.tree.setHeaderHidden(True)
        self.tree.setHeaderLabels(['Container name', 'Number of contents'])
        # self.tree.itemClicked.connect(lambda widget, _: self.delete_by_id_button.setEnabled(True) if widget.text(0) == 'waveforms' else self.delete_by_id_button.setEnabled(False))
        self.tree.itemDoubleClicked.connect(self._show_content_list)
        with ismrmrd.File(file_name, mode='r') as f:
            FileWidget.__populate_tree(self.tree, f, (file_name,))
        
        self.setLayout(QtWidgets.QVBoxLayout())
        button_layout = QtWidgets.QHBoxLayout()
        self.delete_button = QtWidgets.QPushButton(self, text="Delete selected datasets")

        self.repack_button = QtWidgets.QPushButton(self, text="Repack file")
        self.repack_button.clicked.connect(self._repack_file)
        self.delete_button.clicked.connect(self._remove_selected)

        self.delete_button.setShortcut('Del')
        self.delete_button.setToolTip('Delete selected datasets')  
        self.repack_button.setToolTip('Repack the file')

        self.layout().addWidget(self.tree)
        self.layout().addLayout(button_layout)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.repack_button)

    def _remove_selected(self):
        for item in self.tree.selectedItems():
            # print(item)
            if hasattr(item, 'container_keys'): # This is a dataset, we can delete directly
                # item.container.clear()
                print(item.container_keys)
                with ismrmrd.File(item.container_keys[0], mode='r+') as f:
                    container = f
                    del f['/'.join(item.container_keys[1:])]
            else: # This is a content, we need to call parent's correct delete method
                print('No container keys')
                print(item.parent().container_keys)
                with ismrmrd.File(item.parent().container_keys[0], mode='r+') as f:
                    container = f
                    for key in item.parent().container_keys[1:]:
                        container = container[key]
                    
                    if item.text(0) == 'images':
                        container._Container__del_images()
                    elif item.text(0) == 'waveforms':  
                        container._Container__del_waveforms()
                    elif item.text(0) == 'header':
                        container._Container__del_header()
                    elif item.text(0) == 'acquisition':
                        container._Container__del_acquisitions()
                    
            root = self.tree.invisibleRootItem()
            (item.parent() or root).removeChild(item)

    def _repack_file(self):
        print('Repacking the file, this may take a while....')

        rpk_fname = self.file_name + '.rpk'
        os.rename(self.file_name, rpk_fname)
        print(subprocess.run(['h5repack', f'{rpk_fname}', f'{self.file_name}']))
        os.remove(rpk_fname)

    def _show_content_list(self):
        item = self.tree.currentItem()
        if item.text(0) == 'waveforms':
            self._show_waveform_list_popup(item.parent().container_keys)

    def _show_waveform_list_popup(self, item):
        popup = QtWidgets.QDialog(self)
        popup.setWindowTitle('Waveform List')
        popup.setLayout(QtWidgets.QVBoxLayout())
        delete_button = QtWidgets.QPushButton(popup, text="Delete selected")

        with ismrmrd.File(item[0], mode='r') as f:
            waveforms = f['/'.join(item[1:])].waveforms
            self.wf_list_widget = QtWidgets.QTableWidget(len(waveforms), 2, popup)
            self.wf_list_widget.setHorizontalHeaderLabels(['Scan Counter', 'Waveform ID'])
            for i, waveform in enumerate(waveforms):
                self.wf_list_widget.setItem(i, 0, QtWidgets.QTableWidgetItem(str(waveform.scan_counter)))
                self.wf_list_widget.setItem(i, 1, QtWidgets.QTableWidgetItem(str(waveform.waveform_id)))
            # list_widget.setItem([QtWidgets.QTableWidgetItem(waveform.waveform_id) for waveform in waveforms])

        popup.layout().addWidget(self.wf_list_widget)
        popup.layout().addWidget(delete_button)

        # list_widget.itemDoubleClicked.connect(lambda item: self._delete_waveform_by_id(item.text()))
        delete_button.clicked.connect(lambda: self._delete_waveform_by_idx(item, self.wf_list_widget.currentRow()))
        popup.exec()
    
    def _delete_waveform_by_idx(self, item, idx):
        print(f"Deleting waveform {idx} from {'/'.join(item[1:])}")
        with h5py.File(item[0], mode='r+') as f:
            wfs = f['/'.join(item[1:]) + '/waveforms']
            wfs2 = []
            # print(f'Finding and removing waveforms with ID {waveform_id}...')
            for row_i, wf in enumerate(wfs):
                if row_i != idx:
                    wfs2.append(wf)
                    row_i-=1

            del f['/'.join(item[1:]) + '/waveforms']
            f.create_dataset('/'.join(item[1:]) + '/waveforms', maxshape=(None,), chunks=True, data=np.array(wfs2))
        self.wf_list_widget.removeRow(idx)


    @staticmethod
    def __available_contents(container):
        return [key for key in container.available()]

    @staticmethod
    def __populate_tree(node, container, container_keys: tuple[str, ...] = None):

        for item in container:

            child = QtWidgets.QTreeWidgetItem(node, [item, ''])
            child.setExpanded(True)

            for content in FileWidget.__available_contents(container[item]):
                num_contents = 0
                if content == 'waveforms':
                    num_contents = len(container[item].waveforms)
                elif content == 'images':
                    num_contents = len(container[item].images)
                elif content == 'acquisition':
                    num_contents = len(container[item].acquisitions)
                    
                content = QtWidgets.QTreeWidgetItem(child, [content, f'({num_contents})'])
                content.container = container[item]

            child.container_keys = (*container_keys, item) if container_keys else (item,)
            FileWidget.__populate_tree(child, container[item], child.container_keys)

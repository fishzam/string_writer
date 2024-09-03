# -*- coding: utf-8 -*-
"""
/***************************************************************************
 StringWriter
        A QGIS plugin that writes QGIS layers to Surpac string file format

                              -------------------
        begin                : 2024-08-27
        email                : padfish@hotmail.co.uk
 ***************************************************************************/
 
 /***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsPointXY, Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsWkbTypes
from qgis.PyQt.QtWidgets import QFileDialog, QAction, QDialog, QVBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsProjectionSelectionWidget
import os
from datetime import datetime
import math

class StringWriterDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('String Writer')
        self.setLayout(QVBoxLayout())

        self.layerLabel = QLabel('Select Layer', self)
        self.layout().addWidget(self.layerLabel)
        
        self.layerComboBox = QComboBox(self)
        self.layout().addWidget(self.layerComboBox)
        
        self.projectionLabel = QLabel('Select Target CRS', self)
        self.layout().addWidget(self.projectionLabel)

        self.crsSelector = QgsProjectionSelectionWidget(self)
        self.layout().addWidget(self.crsSelector)
        
        self.attributeLabel = QLabel('Select Attribute', self)
        self.layout().addWidget(self.attributeLabel)

        self.fieldComboBox = QComboBox(self)
        self.layout().addWidget(self.fieldComboBox)

        self.zValueLabel = QLabel('Default Z Value (if not available)', self)
        self.layout().addWidget(self.zValueLabel)

        self.zValueInput = QLineEdit(self)
        self.zValueInput.setText("0")  
        self.layout().addWidget(self.zValueInput)

        self.saveButton = QPushButton('Save as String File', self)
        self.layout().addWidget(self.saveButton)

        footer_text = """Surpac String Writer<br>
                         Layer Must Be LineString Or Point"""
        self.footerLabel = QLabel(footer_text, self)
        self.footerLabel.setAlignment(Qt.AlignCenter)  
        self.footerLabel.setWordWrap(True)  
        self.layout().addWidget(self.footerLabel)

        self.populate_layers()

    def populate_layers(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsVectorLayer)]
        self.layerComboBox.clear()
        self.layerComboBox.addItems([layer.name() for layer in layers])

class StringWriter:
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.plugin_dir = os.path.dirname(__file__)
        self.menu = 'String Writer'
        
        self.dlg = StringWriterDialog()
        self.dlg.layerComboBox.currentIndexChanged.connect(self.update_field_combobox)
        self.dlg.saveButton.clicked.connect(self.save_string_file)

        QgsProject.instance().layersAdded.connect(self.dlg.populate_layers)
        QgsProject.instance().layersRemoved.connect(self.dlg.populate_layers)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.action = QAction(QIcon(icon_path), 'String Writer', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu, self.action)

    def unload(self):
        self.iface.removePluginMenu(self.menu, self.action)
        self.iface.removeToolBarIcon(self.action)

        QgsProject.instance().layersAdded.disconnect(self.dlg.populate_layers)
        QgsProject.instance().layersRemoved.disconnect(self.dlg.populate_layers)

    def run(self):
        self.dlg.populate_layers()  
        self.dlg.show()

    def update_field_combobox(self):
        layer_name = self.dlg.layerComboBox.currentText()
        layers = QgsProject.instance().mapLayersByName(layer_name)

        if layers:
            layer = layers[0]
            self.dlg.fieldComboBox.clear()
            self.dlg.fieldComboBox.addItems([field.name() for field in layer.fields()])
        else:
            self.dlg.fieldComboBox.clear() 

    def save_string_file(self):
        layer_name = self.dlg.layerComboBox.currentText()
        layers = QgsProject.instance().mapLayersByName(layer_name)

        if not layers:
            self.iface.messageBar().pushMessage("Error", f"Layer {layer_name} not found.", level=Qgis.Critical)
            return

        layer = layers[0]
        target_crs = self.dlg.crsSelector.crs()

        selected_field_name = self.dlg.fieldComboBox.currentText()
        elev_idx = layer.fields().indexFromName('ELEV')
        has_elev_field = elev_idx != -1
        selected_field_idx = layer.fields().indexFromName(selected_field_name)

        source_crs = layer.crs()
        transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

        try:
            default_z_value = float(self.dlg.zValueInput.text())
        except ValueError:
            default_z_value = 0.0

        save_path, _ = QFileDialog.getSaveFileName(self.dlg, 'Save String File', '', 'Surpac String File (*.str)')

        if save_path:
            current_date = datetime.now().strftime("%d-%b-%y")
            header = f"{layer_name}, {current_date}, Earthworks Surpac Driver,\n" \
                     f"0,    0.000000,    0.000000,    0.000000,    0.000000,    0.000000,    0.000000\n"

            footer = "0,    0.000000,    0.000000,    0.000000,\n0,    0.000000,    0.000000,    0.000000, END\n"

            with open(save_path, 'w') as file:
                file.write(header)

                for feature in layer.getFeatures():
                    geom = feature.geometry()

                    if layer.geometryType() == QgsWkbTypes.LineGeometry:
                        if geom.isMultipart():
                            line_strings = geom.asMultiPolyline()
                        else:
                            line_strings = [geom.asPolyline()]

                        for line in line_strings:
                            for i, point in enumerate(line):
                                transformed_point = transform.transform(QgsPointXY(point.x(), point.y()))

                                try:
                                    vertex = geom.vertexAt(i)
                                    z_value = vertex.z()
                                    if z_value is None or math.isnan(z_value):
                                        z_value = None
                                except:
                                    z_value = None

                                if z_value is None and has_elev_field and feature[elev_idx] is not None:
                                    z_value = feature[elev_idx]

                                if z_value is None or math.isnan(z_value):
                                    z_value = default_z_value

                                x, y = transformed_point.x(), transformed_point.y()

                                selected_field_value = feature[selected_field_idx] if selected_field_idx != -1 else 'None'

                                file.write(f"1, {y:>12.6f}, {x:>12.6f}, {z_value:>12.6f}, {selected_field_value}\n")

                            file.write("0,    0,    0,    0, 0\n")
                
                    elif layer.geometryType() == QgsWkbTypes.PointGeometry:
                        point = geom.asPoint()
                        transformed_point = transform.transform(QgsPointXY(point.x(), point.y()))

                        z_value = None
                        if has_elev_field and feature[elev_idx] is not None:
                            z_value = feature[elev_idx]
                        if z_value is None or math.isnan(z_value):
                            z_value = default_z_value

                        x, y = transformed_point.x(), transformed_point.y()
                        selected_field_value = feature[selected_field_idx] if selected_field_idx != -1 else 'None'

                        file.write(f"1, {y:>12.6f}, {x:>12.6f}, {z_value:>12.6f}, {selected_field_value}\n")
                        file.write("0,    0,    0,    0, 0\n")

                file.write(footer)

            self.iface.messageBar().pushMessage("Success", f"Layer {layer_name} saved as {save_path}", level=Qgis.Info)

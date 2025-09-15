import qt, ctk, slicer
import logging, traceback
import os, json, hashlib, datetime

from pathlib import Path
from typing import Dict, List, Optional

from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from opacity_slicer import OpacitySliderWidget
from loading_dialog import ProcessingDialog


class HistoryTreeWidget(qt.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Configure tree widget
        self.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded)
        self.setMinimumHeight(200)
        self.setFrameStyle(qt.QFrame.StyledPanel | qt.QFrame.Sunken)
        
        # Configure header
        headerFont = self.headerItem().font(0)
        headerFont.setBold(True)
        self.headerItem().setFont(0, headerFont)
        
        self.setHeaderLabels(["Version", "Owner", "Date", "Model"])
        self.setAlternatingRowColors(True)
        self.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.sortItems(2, qt.Qt.DescendingOrder)
        
        # Set column widths
        self.setColumnWidth(0, 300)  # Version column
        self.setColumnWidth(1, 150)  # Owner column
        self.setColumnWidth(2, 200)  # Date column
        self.setColumnWidth(3, 150)  # Model column
        
        # Style sheet for better visual appearance
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #EEEEEE;
            }
            QTreeWidget::item:selected {
                background-color: #E3F2FD;
                color: black;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 6px;
                border: none;
                border-right: 1px solid #CCCCCC;
                border-bottom: 1px solid #CCCCCC;
            }
        """)
                
    def update_history(self, history_data):
        """Update tree with history data"""
        self.clear()
        items = []
        
        for entry in history_data:
            item = qt.QTreeWidgetItem([
                os.path.basename(entry['path']),
                entry['owner'],
                entry['creation_date'],
                entry['model']
            ])
            # Store full path as item data
            item.setData(0, qt.Qt.UserRole, entry['path'])
            items.append(item)
            
        self.addTopLevelItems(items)
        self.resizeColumnToContents(0)

class HistoryWidget(qt.QWidget):
    def __init__(self, logic, modelSelector, expertVersionSelector, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.modelSelector = modelSelector
        self.expertVersionSelector = expertVersionSelector
        self.setup_ui()
        
    def setup_ui(self):
        layout = qt.QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title and description
        titleLayout = qt.QHBoxLayout()
        title = qt.QLabel("Segmentation Version History")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        titleLayout.addWidget(title)
        layout.addLayout(titleLayout)
        
        # History tree
        self.historyTree = HistoryTreeWidget()
        layout.addWidget(self.historyTree)
        
        # Add opacity control
        self.opacityControl = OpacitySliderWidget()
        layout.addWidget(self.opacityControl)
        
        # Comparison settingsa
        comparisonSettings = qt.QGroupBox("Comparison Settings")
        comparisonSettings.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                margin-top: 8px;
                padding: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
        """)
        comparisonLayout = qt.QVBoxLayout(comparisonSettings)
        
        # Add padding checkbox
        self.usePaddingCheckbox = qt.QCheckBox("Tolerant Overlap")
        self.usePaddingCheckbox.setToolTip("Enable to use binary dilation for more tolerant overlap detection")
        comparisonLayout.addWidget(self.usePaddingCheckbox)
        
        layout.addWidget(comparisonSettings)
        
        # Buttons layout
        buttonLayout = qt.QHBoxLayout()
        buttonLayout.setSpacing(8)
        buttonLayout.setAlignment(qt.Qt.AlignCenter)
        
        # Style buttons
        buttonStyle = """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 120px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """
        
        self.loadButton = qt.QPushButton("Load Selected")
        self.loadButton.setStyleSheet(buttonStyle)
        self.loadButton.enabled = False
        buttonLayout.addWidget(self.loadButton)
        
        self.compareButton = qt.QPushButton("Compare")
        self.compareButton.setStyleSheet(buttonStyle)
        self.compareButton.enabled = False
        buttonLayout.addWidget(self.compareButton)
        
        self.showMetadataButton = qt.QPushButton("Show Metadata")
        self.showMetadataButton.setStyleSheet(buttonStyle)
        self.showMetadataButton.enabled = False
        buttonLayout.addWidget(self.showMetadataButton)
        
        layout.addLayout(buttonLayout)
        
        # Legend
        legendBox = qt.QGroupBox("Legend")
        legendBox.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                margin-top: 8px;
                padding: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
        """)
        legendLayout = qt.QVBoxLayout(legendBox)
        legendLayout.setSpacing(8)
        legendLayout.setContentsMargins(8, 8, 8, 8)
        
        # Legend items with icons
        for label, color in [
                ("Added Vessels in Current Version", "#00FF00"),
                ("Removed with respect to Selected History Version", "#FF0000"),
                ("Overlapping Vessels", "#FFFF00"),
                ]:
            itemLayout = qt.QHBoxLayout()
            colorBox = qt.QFrame()
            colorBox.setStyleSheet(f"background-color: {color};")
            colorBox.setFixedSize(16, 16)
            itemLayout.addWidget(colorBox)
            itemLayout.addWidget(qt.QLabel(label))
            itemLayout.addStretch()
            legendLayout.addLayout(itemLayout)
        
        layout.addWidget(legendBox)
        
        # Connect signals
        self.historyTree.itemSelectionChanged.connect(self.onSelectionChanged)
        self.loadButton.clicked.connect(self.onLoadVersion)
        self.compareButton.clicked.connect(self.onCompareVersions)
        self.showMetadataButton.clicked.connect(self.onShowMetadata)


    def onCompareVersions(self):
        """Compare selected version with current"""
        
        # Create and show loading dialog
        loadingDialog = ProcessingDialog(slicer.util.mainWindow())
        loadingDialog.show()
        loadingDialog.update_status("Loading segmentation from history for comparison...")
        
        selected = self.historyTree.selectedItems()
        if not selected:
            loadingDialog.close()
            slicer.util.errorDisplay("No version selected")
            return
        
        # Store version path
        version_path = selected[0].data(0, qt.Qt.UserRole)

        # Load current segmentation through parent widget 
        parent = slicer.modules.vesselverse.widgetRepresentation().self()
        parent.onLoadSegmentation()
        
        current_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        if not current_nodes:
            loadingDialog.close()
            slicer.util.errorDisplay("Failed to load current segmentation")
            return

        # Configure views
        layoutManager = slicer.app.layoutManager()
        self._configureViews(layoutManager)

        # Get current node and version to compare
        current_node = current_nodes[0]
        
        # Load comparison segmentation
        loadingDialog.update_status("Loading comparison segmentation...")
        success = slicer.util.loadSegmentation(version_path)
        if not success:
            slicer.util.errorDisplay(f"Failed to load comparison: {version_path}")
            return
                
        # Get comparison node (the last loaded segmentation)
        comparison_node = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")[-1]

        # Create surface representations and compare
        current_node.CreateClosedSurfaceRepresentation()
        comparison_node.CreateClosedSurfaceRepresentation()

        loadingDialog.update_status("Computing intersection...")
        result_node = compareSegmentations(
            current_node, 
            comparison_node,
            use_padding=self.usePaddingCheckbox.isChecked()
        )
        
        # Update opacity control and cleanup
        if hasattr(self, 'opacityControl'):
            self.opacityControl.updateForNode(result_node)
            
        slicer.mrmlScene.RemoveNode(current_node)
        slicer.mrmlScene.RemoveNode(comparison_node)
        
        loadingDialog.close()

    def _configureViews(self, layoutManager):
        """Configure the layout for comparison view"""
        # Switch to four-up layout
        layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        
        # Hide all volumes in 3D view
        volumeNodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        for volumeNode in volumeNodes:
            displayNode = volumeNode.GetDisplayNode()
            if displayNode:
                displayNode.SetVisibility3D(False)
                displayNode.SetVisibility(False)
        
        # Configure 3D view
        threeDView = layoutManager.threeDWidget(0)
        if threeDView:
            viewNode = threeDView.mrmlViewNode()
            viewNode.SetBoxVisible(False)
            
            # Hide slice views in 3D
            sliceNodes = slicer.util.getNodesByClass('vtkMRMLSliceNode')
            for sliceNode in sliceNodes:
                sliceNode.SetWidgetVisible(False)
                
        # Configure slice views
        for viewName in ["Red", "Yellow", "Green"]:
            sliceWidget = layoutManager.sliceWidget(viewName)
            if sliceWidget:
                sliceController = sliceWidget.sliceController()
                sliceController.setSliceLink(True)
                sliceController.setSliceVisible(False)
                
    def update_history(self, segmentation_path):
        """Update history tree for given segmentation"""
        if not segmentation_path:
            self.historyTree.clear()
            return
        print(f"Updating history for {segmentation_path}")
        history = self.logic.track_history(segmentation_path)
        self.historyTree.update_history(history)
        
    def erase_history(self):
        """Clear history tree"""
        self.historyTree.clear()
        
    def onSelectionChanged(self):
        """Handle tree selection changes"""
        selected = self.historyTree.selectedItems()
        self.loadButton.enabled = len(selected) > 0
        self.compareButton.enabled = len(selected) > 0
        self.showMetadataButton.enabled = len(selected) > 0
        
    def onLoadVersion(self):
        """Load selected version"""
        selected = self.historyTree.selectedItems()
        
        if not selected:
            return
            
        # Get full path from item data
        version_path = selected[0].data(0, qt.Qt.UserRole)
        model = version_path.split('/')[-2]
        #Update model selector to reflect the loaded segmentation
        self.modelSelector.setCurrentText(model)
        if model == "ExpertAnnotations":
            #Update expert version selector to reflect the loaded segmentation
            parts = Path(version_path).stem.split('_')
            expertID = parts[2]
            timestamp = '_'.join(parts[3:])
            self.expertVersionSelector.setCurrentText(f"{expertID} ({timestamp})")
            
        # Clear current segmentation
        self.logic.current_segmentation_path = version_path
        self.logic.closeAllSegmentations()
        
        # Load selected version
        success = self.logic.loadSegmentation(Path(version_path))
        if not success:
            slicer.util.errorDisplay(f"Failed to load segmentation: {version_path}")

    def onKeepCurrent(self):
        # Get current segmentation node
        current_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        if not current_nodes:
            slicer.util.errorDisplay("No current segmentation loaded")
            return
        
        # if there are multiple segmentations loaded, the Segment Editor will only work with the first one (tell in a message box)
        if len(current_nodes) > 1:
            slicer.util.messageBox(f"Segment Editor will only work with the first segmentation loaded: CURRENT")
        
        # Keep only the current segmentation node and set its color to green
        current_node = current_nodes[0]
        current_segmentation = current_node.GetSegmentation()
        for segmentId in range(current_segmentation.GetNumberOfSegments()):
            segment = current_segmentation.GetNthSegment(segmentId)
            segment.SetColor(0.0, 1.0, 0.0)  # Green
            
        current_node.SetName("CURRENT")
        current_node.Modified()
        
        # Remove any other segmentation nodes
        for node in current_nodes[1:]:
            slicer.mrmlScene.RemoveNode(node)
    
    def onShowMetadata(self):
        """Show metadata for selected version"""
        selected = self.historyTree.selectedItems()
        if not selected:
            return
        
        version_path = selected[0].data(0, qt.Qt.UserRole)
        metadata = self.logic.getMetadata(version_path)
        
        if not metadata:
            slicer.util.errorDisplay("No metadata found for selected version")
            return
        # Remove affine and header from metadata
        metadata.pop('affine', None)
        metadata.pop('header', None)
        
        # Format JSON with proper indentation and encode special characters
        metadata_str = json.dumps(metadata, indent=4, ensure_ascii=False)

        # Display in messageBox with monospace font and increased size
        slicer.util.messageBox(metadata_str, windowTitle="JSON Viewer", icon=qt.QMessageBox.Information, 
                            stylesheet="QMessageBox { font-family: monospace; font-size: 12px; min-width: 600px; }")

class VesselVerse(ScriptedLoadableModule):
    def __init__(self, parent):
        
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "VesselVerse"
        self.parent.icon = qt.QIcon(os.path.join(os.path.dirname(__file__), 'Resources', 'Icons', 'icon_V.png'))
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Daniele Falcetta (EURECOM - Biot, France)"]
        self.parent.helpText = """
            Vessel segmentation management module for data version tracking.
            Allows loading, modification, and version control of vessel segmentations.
            """
        self.parent.acknowledgementText = """
            This module was developed for the VesselVerse project.
            """
        
        # Register module path only during initialization
        settings = qt.QSettings()
        currentPaths = settings.value("Modules/AdditionalPaths") or []
        if isinstance(currentPaths, str):
            currentPaths = [currentPaths]
        elif isinstance(currentPaths, tuple):
            currentPaths = list(currentPaths)
        
        modulePath = os.path.dirname(os.path.abspath(__file__))
        if modulePath not in currentPaths:
            currentPaths.append(modulePath)
            settings.setValue("Modules/AdditionalPaths", currentPaths)
    
    def _registerModulePath(self):
        """Register the module path in Slicer settings"""
        import os
        settings = qt.QSettings()
        currentPaths = settings.value("Modules/AdditionalPaths") or []
        if isinstance(currentPaths, str):
            currentPaths = [currentPaths]
        
        # Get the absolute path to the module directory
        modulePath = os.path.dirname(os.path.abspath(__file__))
        
        if modulePath not in currentPaths:
            currentPaths.append(modulePath)
            settings.setValue("Modules/AdditionalPaths", currentPaths)

class VesselVerseWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False
    
    def cleanup(self):
        """Called when the module is closed"""
        self.removeObservers()
        
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        
        # Create main collapsible buttons 
        self.logic = VesselVerseLogic()
        try:
            # Collapse  and Hide the Reload and Test Panel
            self.reloadCollapsibleButton.collapsed = True
            self.reloadCollapsibleButton.visible = False    
        except:
            print("Reload and Test Panel not found: ignoring this step")
            
        
        # Collapse Data Probe section
        dataProbeCollapsibleButton = slicer.util.findChild(slicer.util.mainWindow(), 'DataProbeCollapsibleWidget')
        if dataProbeCollapsibleButton:
            dataProbeCollapsibleButton.collapsed = True
        
        # Create Dataset Selection Section
        datasetSection = qt.QGroupBox()
        datasetSection.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 1px solid: #8d8d8d;
                border-radius: 4px;
                margin-top: 8px;
                padding: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
                font-weight: bold;
                font-size: 13px;
            }
        """)

        datasetLayout = qt.QVBoxLayout(datasetSection)
        datasetLayout.setSpacing(8)

        self.datasetSelectorDropDown = qt.QComboBox()
        from model_config.model_config import dataset_registry
        dataset_names = list(dataset_registry.datasets.keys())
        self.datasetSelectorDropDown.addItems(dataset_names)  # Load dataset names dynamically

        self.datasetSelectorDropDown.setStyleSheet("""
            QComboBox {
                border: 2px solid #8d8d8d;
                border-radius: 6px;
                padding: 6px;
                font-size: 14px;
                background-color: white;
            }
            QComboBox:hover {
                border: 2px solid #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                width: 14px;
                height: 14px;
            }
        """)

        datasetLabel = qt.QLabel("Select Dataset:")
        datasetLabel.setStyleSheet("font-size: 13px; font-weight: bold; padding-bottom: 4px;")

        datasetLayout.addWidget(datasetLabel)
        datasetLayout.addWidget(self.datasetSelectorDropDown)
        self.layout.addWidget(datasetSection)

        # Connect selection change
        self.datasetSelectorDropDown.currentIndexChanged.connect(self.onDatasetSelectionChanged)


        # Add spacing
        self.layout.addSpacing(10)
        
        # Create main collapsible buttons with spacing
        inputsCollapsibleButton = ctk.ctkCollapsibleButton()
        inputsCollapsibleButton.text = "Inputs"
        self.layout.addWidget(inputsCollapsibleButton)
        inputsFormLayout = qt.QFormLayout(inputsCollapsibleButton)
        inputsFormLayout.setSpacing(10)  # Increase spacing between rows
        inputsFormLayout.setContentsMargins(10, 10, 10, 10)  # Add margins

        # Input Image Section
        imageSection = qt.QGroupBox("Image Selection")
        imageLayout = qt.QVBoxLayout(imageSection)
        imageLayout.setSpacing(8)
        
        self.imagePathSelector = ctk.ctkPathLineEdit()
        self.imagePathSelector.filters = ctk.ctkPathLineEdit.Files
        self.imagePathSelector.nameFilters = ["Image files (*.nii.gz)"]
        # Find and modify the QToolButton
        for widget in self.imagePathSelector.findChildren(qt.QToolButton):
            widget.setText("▼")
            widget.setToolTip("Browse files")  # Change tooltip
            
        self.imagePathSelector.setStyleSheet("QComboBox::drop-down {border: none;} QComboBox::down-arrow {border: none; width: 0px;}")
        imageLayout.addWidget(self.imagePathSelector)
        
        self.loadImageButton = qt.QPushButton("Load Image")
        self.loadImageButton.setMinimumHeight(30)
        imageLayout.addWidget(self.loadImageButton)
        
        inputsFormLayout.addRow(imageSection)

        # Model Selection Section
        modelSection = qt.QGroupBox("Segmentation Model Selection")
        modelLayout = qt.QVBoxLayout(modelSection)
        modelLayout.setSpacing(8)
        
        # First model selector
        firstModelLayout = qt.QGridLayout()
        firstModelLayout.setSpacing(5)
        
        self.modelSelector = qt.QComboBox()
        firstModelLayout.addWidget(qt.QLabel("Model Type:"), 0, 0)
        firstModelLayout.addWidget(self.modelSelector, 0, 1)
        
        self.expertVersionSelector = qt.QComboBox()
        self.expertVersionSelector.setVisible(False)
        firstModelLayout.addWidget(qt.QLabel("Expert Version:"), 1, 0)
        firstModelLayout.addWidget(self.expertVersionSelector, 1, 1)
        
        self.loadSegmentationButton = qt.QPushButton("Load Segmentation")
        self.loadSegmentationButton.setMinimumHeight(30)
        firstModelLayout.addWidget(self.loadSegmentationButton, 2, 0, 1, 2)
        
        modelLayout.addLayout(firstModelLayout)
        
        # Second model selector (in collapsible section)
        secondModelCollapsible = ctk.ctkCollapsibleButton()
        secondModelCollapsible.text = "Second Segmentation"
        secondModelCollapsible.collapsed = True
        secondModelLayout = qt.QGridLayout(secondModelCollapsible)
        secondModelLayout.setSpacing(5)
        
        self.modelSelector2 = qt.QComboBox()
        #self.modelSelector2.addItems(modelTypes)
        secondModelLayout.addWidget(qt.QLabel("Model Type 2:"), 0, 0)
        secondModelLayout.addWidget(self.modelSelector2, 0, 1)
        
        self.expertVersionSelector2 = qt.QComboBox()
        self.expertVersionSelector2.setVisible(False)
        secondModelLayout.addWidget(qt.QLabel("Expert Version 2:"), 1, 0)
        secondModelLayout.addWidget(self.expertVersionSelector2, 1, 1)
        
        self.loadSegmentationButton2 = qt.QPushButton("Load Segmentation 2")
        self.loadSegmentationButton2.setMinimumHeight(30)
        secondModelLayout.addWidget(self.loadSegmentationButton2, 2, 0, 1, 2)
        
        modelLayout.addWidget(secondModelCollapsible)
        inputsFormLayout.addRow(modelSection)
        
        # Editing Section
        editSection = qt.QGroupBox("Segmentation Editing")
        editLayout = qt.QVBoxLayout(editSection)
        editLayout.setSpacing(8)

        # Initialize segmentEditorButton
        self.segmentEditorButton = qt.QPushButton("Open Segment Editor")
        self.segmentEditorButton.setEnabled(False)
        self.segmentEditorButton.setMinimumHeight(30)
        self.segmentEditorButton.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        editLayout.addWidget(self.segmentEditorButton)

        inputsFormLayout.addRow(editSection)
        
        
        # Add History Section
        self.layout.addSpacing(10)
        historyCollapsibleButton = ctk.ctkCollapsibleButton()
        historyCollapsibleButton.text = "Version History"
        self.layout.addWidget(historyCollapsibleButton)
        
        # Create history widget
        self.historyWidget = HistoryWidget(self.logic, self.modelSelector, self.expertVersionSelector)
        historyLayout = qt.QVBoxLayout(historyCollapsibleButton)
        historyLayout.setSpacing(8)
        historyLayout.setContentsMargins(10, 10, 10, 10)
        historyLayout.addWidget(self.historyWidget)

        # Connect signals
        self.loadImageButton.connect('clicked(bool)', self.onLoadImage)
        self.loadSegmentationButton.connect('clicked(bool)', self.onLoadSegmentation)
        self.loadSegmentationButton2.connect('clicked(bool)', self.onLoadSegmentation2)
        self.segmentEditorButton.connect('clicked(bool)', self.onOpenSegmentEditor)
        self.modelSelector.currentTextChanged.connect(self.onModelSelectionChanged1)
        self.modelSelector2.currentTextChanged.connect(self.onModelSelectionChanged2)

        # Style buttons
        for button in [self.loadImageButton, self.loadSegmentationButton, 
                    self.loadSegmentationButton2, self.segmentEditorButton]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                }
            """)
        self.forceDatasetSelection(dataset_names=dataset_names)
        
    def forceDatasetSelection(self, dataset_names=None):
        if not dataset_names:
            from model_config.model_config import dataset_registry
            dataset_names = list(dataset_registry.datasets.keys())
        
        print(f"Available datasets: {dataset_names}")
        
        """Display a message box to force the user to select a dataset before using the tool."""
        dialog = qt.QDialog()
        dialog.setWindowTitle("Select Dataset")
        dialog.setModal(True)
        dialog.resize(200, 50)  # Make the dialog larger

        layout = qt.QVBoxLayout(dialog)

        # # Title Label
        # titleLabel = qt.QLabel("Please select a Dataset:")
        # titleLabel.setStyleSheet("font-size: 14px; font-weight: bold;")
        # titleLabel.setAlignment(qt.Qt.AlignCenter)
        # layout.addWidget(titleLabel)

        # Dataset Dropdown
        self.datasetSelector = qt.QComboBox()
        self.datasetSelector.addItems(dataset_names)  # Add more datasets as needed
        self.datasetSelector.setStyleSheet("""
            QComboBox {
                border: 2px solid #CCCCCC;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                background-color: white;
            }
            QComboBox:hover {
                border: 2px solid #2196F3;
            }
        """)
        layout.addWidget(self.datasetSelector)

        # Buttons Layout
        buttonLayout = qt.QHBoxLayout()

        # Confirm Button
        confirmButton = qt.QPushButton("Confirm Selection")
        confirmButton.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        confirmButton.clicked.connect(lambda: self.applyDatasetSelection(dialog))
        buttonLayout.addWidget(confirmButton)

        # Close Slicer Button
        closeButton = qt.QPushButton("Close Slicer")
        closeButton.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
            QPushButton:pressed {
                background-color: #7F0000;
            }
        """)
        closeButton.clicked.connect(lambda: self.closeSlicer(dialog))
        buttonLayout.addWidget(closeButton)

        layout.addLayout(buttonLayout)
        dialog.exec_()

    def applyDatasetSelection(self, dialog):
        """Set the selected dataset and update paths/configurations dynamically."""

        selectedDataset = self.datasetSelector.currentText
        from model_config.model_config import dataset_registry
        dataset_config = dataset_registry.get_dataset(selectedDataset)

        if dataset_config:
            base_path = dataset_config.base_path.resolve()  # Extract base_path dynamically
            print(f"Selected Dataset: {selectedDataset}")
            print(f"Base Path: {base_path}")
            
            if 'IXI' in str(base_path):
                base_path_selector = Path(base_path) / 'IXI_TOT'
            elif 'COW' in str(base_path):
                base_path_selector = Path(base_path) / 'COW_TOT'
            else:
                assert(), f"Unknown dataset: {base_path}"
            
            self.logic.setDataset(base_path)  # Pass base_path instead of just the name
            # Update UI components
            self.imagePathSelector.setCurrentPath(str(base_path_selector))
            supported_models = [model for model in dataset_config.supported_models if '_TOT' not in model]
            self.modelSelector.clear()
            self.modelSelector.addItems(supported_models)
            self.modelSelector2.clear()
            self.modelSelector2.addItems(supported_models)
            self.datasetSelectorDropDown.setCurrentText(selectedDataset)
            #slicer.util.infoDisplay(f"Dataset '{selectedDataset}' loaded successfully.\nBase Path: {base_path}", windowTitle="Dataset Selected")

            dialog.accept()  # Close dialog after selection
        else:
            slicer.util.errorDisplay(f"Error: Dataset '{selectedDataset}' not found in registry!")


    def closeSlicer(self, dialog):
        """Close 3D Slicer application."""
        slicer.util.exit()

    def onDatasetSelectionChanged(self):
        """Handles dataset selection change dynamically."""
        selectedDataset = self.datasetSelectorDropDown.currentText

        # Retrieve dataset configuration
        from model_config.model_config import dataset_registry
        dataset_config = dataset_registry.get_dataset(selectedDataset)
        if not dataset_config:
            slicer.util.errorDisplay(f"Error: Dataset '{selectedDataset}' not found!")
            slice.util.infoDisplay(f"Available datasets: {list(dataset_registry.datasets.keys())}")
            return

        # Update dataset in logic
        base_path = dataset_config.base_path.resolve()
        print(f"Selected Dataset: {selectedDataset}")
        print(f"Base Path: {base_path}")
        print("\n\n\n\n\n")
        self.logic.setDataset(base_path)

        # Update image selector path
        if "IXI" in str(base_path):
            self.imagePathSelector.setCurrentPath(str(base_path / "IXI_TOT"))
        elif "COW" in str(base_path):
            self.imagePathSelector.setCurrentPath(str(base_path / "COW_TOT"))
        else:
            slicer.util.errorDisplay(f"Error: Unknown dataset '{selectedDataset}'")
            return
        # Update segmentation models
        supported_models = [model for model in dataset_config.supported_models if '_TOT' not in model]
        self.modelSelector.clear()
        self.modelSelector.addItems(supported_models)
        self.modelSelector2.clear()
        self.modelSelector2.addItems(supported_models)

        # Clear history and refresh UI
        self.historyWidget.erase_history()
        
        # Cancel all the loaded images/segmentations
        self.logic.clearScene()
        self.modelSelector.setCurrentIndex(0)
        
        # Open segmentation editor button should be disabled
        self.segmentEditorButton.setEnabled(False)
        print(f"Dataset changed to: {selectedDataset}")

        
    def onLoadImage(self):
        """Load the selected input image"""
        imagePath = Path(self.imagePathSelector.currentPath)
        if not imagePath.exists() or not imagePath.is_file() or not imagePath.suffix == ".gz":
            slicer.util.messageBox("Please select a valid input image")
            return

        # Clear everything from the scene
        self.logic.clearScene()
        self.historyWidget.erase_history()
        self.modelSelector.setCurrentIndex(0)
            
        # Load the image
        success = slicer.util.loadVolume(str(imagePath))
        if not success:
            slicer.util.messageBox("Failed to load image")
            return
        
        # Disable segment editor and save buttons until segmentation is loaded
        self.segmentEditorButton.setEnabled(False)

    def loadSegmentationW(self, for_comparison=False):
        """
        Load segmentation based on selected model
        Args:
            for_comparison (bool): If True, loads second segmentation for comparison
        """
        # Setup dialog if comparison mode
        loadingDialog = None
        if for_comparison:
            if not slicer.util.getNodesByClass("vtkMRMLSegmentationNode"):
                slicer.util.errorDisplay("No current segmentation loaded: loading the first segmentation")
                
            self.loadSegmentationW(for_comparison=False)
            loadingDialog = ProcessingDialog(slicer.util.mainWindow())
            loadingDialog.show()
            loadingDialog.update_status("Loading second segmentation for comparison...")
        
        try:
            # Get correct selectors based on mode
            modelSelector = self.modelSelector2 if for_comparison else self.modelSelector
            expertVersionSelector = self.expertVersionSelector2 if for_comparison else self.expertVersionSelector
            
            # Validate image path
            imagePath = Path(self.imagePathSelector.currentPath)
            if not imagePath.exists() or not imagePath.is_file() or not imagePath.suffix == ".gz":
                slicer.util.messageBox("Please select an input image first")
                return
            
            # Load image if needed
            elif not slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode'):
                slicer.util.messageBox("Proceeding to load the segmentation together with the corresponding image...")
                self.onLoadImage()

            # Get segmentation path
            modelType = modelSelector.currentText
            if modelType in ["ExpertAnnotations", "ExpertVAL"]:
                current_idx = expertVersionSelector.currentIndex
                if current_idx < 0:
                    if loadingDialog: loadingDialog.close()
                    slicer.util.messageBox("Please select an expert annotation version")
                    return
                    
                expertData = expertVersionSelector.itemData(current_idx)
                if not expertData:
                    if loadingDialog: loadingDialog.close()
                    slicer.util.messageBox("No expert annotation selected")
                    return
                segPath = Path(expertData)
            else:    
                segPath = self.logic.dataset.get_model_path(imagePath, modelType)
                

            if for_comparison:
                # Comparison mode specific logic
                layoutManager = slicer.app.layoutManager()
                layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
                
                current_node = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")[0]
                
                if not slicer.util.loadSegmentation(str(segPath)):
                    slicer.util.errorDisplay(f"Failed to load comparison: {segPath}")
                    return
                    
                comparison_node = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")[-1]
                
                if loadingDialog:
                    loadingDialog.update_status("Creating surface representations...")
                
                # Create surface representations
                for node in [current_node, comparison_node]:
                    node.CreateClosedSurfaceRepresentation()
                
                # Compare and cleanup
                if loadingDialog:
                    loadingDialog.update_status("Computing intersection...")
                result_node = compareSegmentations(
                    current_node,
                    comparison_node,
                    use_padding=self.historyWidget.usePaddingCheckbox.isChecked())
                
                for node in [current_node, comparison_node]:
                    slicer.mrmlScene.RemoveNode(node)
                    
                # Update opacity control
                if hasattr(self.historyWidget, 'opacityControl'):
                    self.historyWidget.opacityControl.updateForNode(result_node)
                    
            else:
                # Normal mode specific logic
                self.logic.current_segmentation_path = segPath
                self.logic.closeAllSegmentations()
                
                success = self.logic.loadSegmentation(segPath)
                if success:
                    self.segmentEditorButton.setEnabled(True)
                    print(f"Segmentation loaded: {segPath}")
                    self.historyWidget.update_history(str(segPath))
                    
                    segNode = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
                    if segNode:
                        segNode[0].Modified()
                        # Rename segment to match opacity slider naming
                        segment = segNode[0].GetSegmentation().GetNthSegment(0)
                        segment.SetName("Segmentation :")
                        
                        # Update opacity control
                        if hasattr(self.historyWidget, 'opacityControl'):
                            self.historyWidget.opacityControl.updateForNode(segNode[0])
                else:
                    slicer.util.messageBox("Failed to load segmentation")
                    self.segmentEditorButton.setEnabled(False)

        except Exception as e:
            print(f"Error loading segmentation: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            slicer.util.messageBox(f"Error loading segmentation: {str(e)} - Maybe you need to load the image first")
        finally:
            if loadingDialog:
                loadingDialog.close()

    # Replace original methods with calls to the new unified function
    def onLoadSegmentation(self):
        """Load corresponding segmentation based on selected model"""
        self.loadSegmentationW(for_comparison=False)

    def onLoadSegmentation2(self):
        """Load corresponding segmentation based on selected model for comparison"""
        self.loadSegmentationW(for_comparison=True)                
    
    def onReturnAndSave(self):
        """Save modifications and return to VesselVerse"""
        try:
            # Check Expert ID
            if not self.expertIDInput.text:
                slicer.util.messageBox("Please enter an Expert ID")
                return
            if not self.expertIDInput.text.isalnum():
                slicer.util.messageBox("Expert ID must be alphanumeric (no spaces or special characters)")
                return

            # Get current segmentation
            segmentationNode = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
            if not segmentationNode:
                slicer.util.messageBox("No segmentation found to save")
                return

            # Get original image path
            imagePath = Path(self.imagePathSelector.currentPath)
            if not imagePath.exists():
                slicer.util.messageBox("No input image selected")
                return

            messageBox = qt.QMessageBox()
            messageBox.setWindowTitle("Save?")
            messageBox.setText("Are you sure you want to save all changes and return to VesselVerse?")
            messageBox.setStandardButtons(qt.QMessageBox.Yes | qt.QMessageBox.No)
            messageBox.setDefaultButton(qt.QMessageBox.No)
            
            response = messageBox.exec_()
            if response == qt.QMessageBox.No:
                return
            
            # Save modifications
            self.logic.saveModifiedSegmentation(
                segmentationNode[0],
                imagePath,
                self.expertIDInput.text,
                self.notesText.toPlainText(),
                self.modelSelector.currentText,
                original_segmentation_path=self.logic.current_segmentation_path
            )

            # Update expert versions and history
            self.updateExpertVersions(self.expertVersionSelector, self.modelSelector.currentText)
            
            # Return to VesselVerse
            self._disconnectSegmentEditorSignals()
            self._removeReturnButton()
            qt.QTimer.singleShot(100, self._switchToVesselVerse)

            slicer.util.messageBox("Segmentation saved successfully!")

        except Exception as e:
            print(f"Error saving and returning: {str(e)}")
            slicer.util.errorDisplay(f"Error: {str(e)}")
    
    
    
                                
    def onModelSelectionChanged(self, modelType, selector):
        """Handle model type selection changes"""
        if modelType in ["ExpertAnnotations", "ExpertVAL"]:
            self.updateExpertVersions(selector, modelType)
            selector.setVisible(True)
        else:
            selector.setVisible(False)
            
    def onModelSelectionChanged1(self, modelType):
        self.onModelSelectionChanged(modelType, self.expertVersionSelector)
        
    def onModelSelectionChanged2(self, modelType):
        self.onModelSelectionChanged(modelType, self.expertVersionSelector2)

    def updateExpertVersions(self, selector, modelType=None):
        print(f"Updating expert versions for {modelType}")
        """Update available expert versions based on current image"""
        selector.clear()
        
        imagePath = Path(self.imagePathSelector.currentPath)
        if not imagePath.exists():
            return     
        # Get image ID from filename (e.g., "IXI022-Guys-0701-MRA.nii.gz" -> "IXI022")
        imageID = imagePath.stem.split('-')[0]
        
        # Get all expert annotations for this image
        expertFiles = list(self.logic.dataset.paths[f"{modelType}"].glob(f"{imageID}/{imageID}_expert_*.nii.gz"))
        expertFiles = sorted(
                        expertFiles,
                        key=lambda x: datetime.datetime.strptime(x.stem.replace('.nii', '')[-15:], '%Y%m%d_%H%M%S'),
                        reverse=True)
        
        if not expertFiles:
            selector.addItem("No expert annotations available", None)
            selector.setEnabled(False)
            return
            
        selector.setEnabled(True)
        for filepath in expertFiles:
            # Extract expert ID and timestamp from filename
            # Format: IXI022_expert_E01_20250120_215410.nii.gz
            parts = Path(filepath).stem.replace('.nii', '').split('_')
            expertID = parts[-3]
            timestamp = '_'.join(parts[-2:])
            assert len(timestamp) == 15, f"Timestamp length is {len(timestamp)} instead of 15 ({timestamp})"
            # Store the full path as string in the item data
            selector.addItem(f"{expertID} ({timestamp})", str(filepath))
            
        # Set the first item as selected by default
        if expertFiles:
                selector.setCurrentIndex(0)
    
    def onOpenSegmentEditor(self):
        """Open the Segment Editor module configured for the current segmentation"""
        self.onLoadSegmentation()
        self.historyWidget.onKeepCurrent()
        
        # Get current segmentation
        segmentationNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        if not segmentationNodes:
            slicer.util.messageBox("No segmentation loaded")
            return

        # Get current volume node
        volumeNode = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        if not volumeNode:
            slicer.util.messageBox("No volume loaded")
            return

        # Add input dialog for Expert ID
        result = qt.QInputDialog.getText(
            slicer.util.mainWindow(),
            "Expert ID", 
            "Enter your Expert ID:",
            qt.QLineEdit.Normal
        )
        expertID = result

        if not expertID:
            slicer.util.messageBox("Returning (Expert ID is required to open Segment Editor)")
            return

        # Validate ID is alphanumeric
        if not expertID.isalnum():
            slicer.util.messageBox("Expert ID must be alphanumeric (no spaces or special characters)")
            return
        
        try:
            # Switch to Segment Editor module safely
            slicer.util.selectModule("SegmentEditor")

            # Get the SegmentEditor module widget
            segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor

            # Get or create a segment editor node
            segmentEditorNode = slicer.mrmlScene.GetSingletonNode("SegmentEditor", "vtkMRMLSegmentEditorNode")
            if not segmentEditorNode:
                segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
                segmentEditorNode.SetName("SegmentEditor")
                slicer.mrmlScene.AddNode(segmentEditorNode)
            
            # Set up the segment editor
            segmentEditorWidget.setSegmentationNode(segmentationNodes[0])
            segmentEditorWidget.setSourceVolumeNode(volumeNode[0])
            segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)

            # Get the parent widget of the Segment Editor
            segmentEditorParent = slicer.modules.segmenteditor.widgetRepresentation()
            
            # Control panel setup
            controlPanel = qt.QFrame()
            controlPanel.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 4px; padding: 8px; }")
            controlLayout = qt.QVBoxLayout(controlPanel)

            # Save/Return button at top
            self.returnAndSaveButton = qt.QPushButton("Save and Return to VesselVerse")
            self.returnAndSaveButton.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #1976D2; }
                QPushButton:pressed { background-color: #0D47A1; }
            """)
            controlLayout.addWidget(self.returnAndSaveButton)

            # Expert info in box
            expertBox = qt.QGroupBox("Expert Information")
            expertBox.setStyleSheet("""
                QGroupBox {
                    background-color: white;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding: 8px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 3px;
                }
            """)
            expertLayout = qt.QVBoxLayout(expertBox)

            # Expert ID input
            idLayout = qt.QHBoxLayout()
            idLayout.addWidget(qt.QLabel("Expert ID:"))
            self.expertIDInput = qt.QLineEdit()
            self.expertIDInput.setText(expertID)  # Set the entered ID as default
            idLayout.addWidget(self.expertIDInput)
            expertLayout.addLayout(idLayout)

            # Notes input
            expertLayout.addWidget(qt.QLabel("Notes:"))
            self.notesText = qt.QTextEdit()
            self.notesText.setMaximumHeight(80)
            self.notesText.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                }
            """)
            expertLayout.addWidget(self.notesText)
            controlLayout.addWidget(expertBox)
            
            # Add the control panel to the Segment Editor
            layout = segmentEditorParent.layout()
            layout.insertWidget(0, controlPanel)
            
            # Connect the button click
            self.returnAndSaveButton.clicked.connect(self.onReturnAndSave)

            self.returnWithoutSaveButton = qt.QPushButton("Return without Saving")
            self.returnWithoutSaveButton.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d32f2f; }
            QPushButton:pressed { background-color: #b71c1c; }
            """)
            controlLayout.addWidget(self.returnWithoutSaveButton)

            # Connect button click
            self.returnWithoutSaveButton.clicked.connect(self.onReturnWithoutSave)

            
            # Create an opacity control widget
            self.opacityControl = OpacitySliderWidget()
            self.opacityControl.updateForNode(segmentationNodes[0])
            
            # Add the opacity control
            layout.insertWidget(1, self.opacityControl)
        except Exception as e:
            print(f"Error setting up Segment Editor: {str(e)}")
            slicer.util.errorDisplay("Error setting up Segment Editor")
            
    def onReturnWithoutSave(self):
        """Return to VesselVerse without saving changes"""
        messageBox = qt.QMessageBox()
        messageBox.setWindowTitle("Discard Changes?")
        messageBox.setText("Are you sure you want to discard all changes and return to VesselVerse?")
        messageBox.setStandardButtons(qt.QMessageBox.Yes | qt.QMessageBox.No)
        messageBox.setDefaultButton(qt.QMessageBox.No)
        
        response = messageBox.exec_()
        if response == qt.QMessageBox.Yes:
            self._disconnectSegmentEditorSignals()
            self._removeReturnButton()
            qt.QTimer.singleShot(100, self._switchToVesselVerse)
    
    def returnToVesselVerse(self):
        """Return to VesselVerse module safely"""
        try:
            # Disconnect any potential previous connections
            self._disconnectSegmentEditorSignals()
            
            # Remove the return button before switching modules
            self._removeReturnButton()
            
            # Switch modules using a single timer call
            qt.QTimer.singleShot(100, self._switchToVesselVerse)
            
        except Exception as e:
            print(f"Error returning to VesselVerse: {str(e)}")
            slicer.util.errorDisplay("Error returning to VesselVerse")
            
    def _switchToVesselVerse(self):
        """Switch to VesselVerse module"""
        try:
            # Switch module
            slicer.util.selectModule("VesselVerse")
            
            # Force a single layout update
            layoutManager = slicer.app.layoutManager()
            if layoutManager:
                layoutManager.setLayout(layoutManager.layout)
                
            # Update the history widget
            if hasattr(self, 'historyWidget'):
                self.historyWidget.update_history(str(self.logic.current_segmentation_path))
                
            self.onLoadSegmentation()
        except Exception as e:
            print(f"Error in module switch: {str(e)}")
            slicer.util.errorDisplay("Error switching modules")
            
    def _disconnectSegmentEditorSignals(self):
        """Disconnect any signals from the Segment Editor"""
        try:
            segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation()
            if segmentEditorWidget:
                # Disconnect any existing signals/observers
                if hasattr(segmentEditorWidget, 'editor'):
                    segmentEditorWidget.editor.removeObservers()
        except Exception as e:
            print(f"Error disconnecting signals: {str(e)}")
            
    def _removeReturnButton(self):
        """Remove controls from Segment Editor"""
        try:
            segmentEditorParent = slicer.modules.segmenteditor.widgetRepresentation()
            if segmentEditorParent:
                for child in segmentEditorParent.children():
                    # Remove control panel with expert info and save button
                    if isinstance(child, qt.QFrame):
                        child.setParent(None)
                        child.deleteLater()
                    # Remove opacity slider
                    if isinstance(child, OpacitySliderWidget):
                        child.setParent(None)
                        child.deleteLater()
                        
        except Exception as e:
            print(f"Error removing controls: {str(e)}")



    def _safeModuleSwitch(self):
        """Safely switch back to VesselVerse module"""
        try:
            # Switch back to VesselVerse module
            slicer.util.selectModule("VesselVerse")
            
            # Get the Segment Editor widget
            segmentEditorParent = slicer.modules.segmenteditor.widgetRepresentation()
            if segmentEditorParent:
                # Find and remove the return button
                for child in segmentEditorParent.children():
                    if isinstance(child, qt.QPushButton) and child.text == "Return to VesselVerse":
                        child.setParent(None)
                        child.deleteLater()
                        break
        except Exception as e:
            print(f"Error in safe module switch: {str(e)}")
            slicer.util.errorDisplay("Error switching modules")
    

            
class VesselVerseLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

    def setDataset(self, DATA_PATH: Path = None):
        if DATA_PATH:
            self.base_path = DATA_PATH.resolve()
        else:
            print("No dataset path provided, exiting...")
            return
        self.dataset = Dataset(self.base_path)
        self.model_metadata_path = self.base_path / "model_metadata"
        self.expert_metadata_path = self.base_path / "metadata"
        self.expert_metadata_VAL_path = self.base_path / "metadata_expert_val"
        self.current_segmentation_path = None
        self.reload_metadata()
        print(f"Dataset updated to: {DATA_PATH}")
        
    def reload_metadata(self):
        """Reload metadata files"""
        self.model_metadata = self._load_model_metadata()
        self.expert_metadata = self._load_expert_metadata()
        self.expert_VAL_metadata = self._load_expert_metadata(VAL=True)
    
    def _load_expert_metadata(self, VAL=False) -> Dict:
        """Load all expert annotation metadata files."""
        metadata = {}
        expert_metadata_path = self.expert_metadata_VAL_path if VAL else self.expert_metadata_path
        for json_file in expert_metadata_path.glob("*_expert_metadata.json"):
            with open(json_file) as f:
                print(f"Loading expert metadata: {json_file}")
                print(f"Metadata: {json_file.stem.split('_')[0]}")
                metadata[json_file.stem.split('_')[0]] = json.load(f)
        return metadata

    def _load_model_metadata(self) -> Dict:
        """Load all model metadata files."""
        metadata = {}
        for model_config in registry.models.values():
            json_file = self.model_metadata_path / f"{model_config.name}_metadata.json"
            if json_file.exists():
                with open(json_file) as f:
                    print(f"Loading model metadata for {model_config.name}")
                    metadata[model_config.name] = json.load(f)
        return metadata
    
    def clearScene(self):
        """Clear all nodes from the scene"""
        slicer.mrmlScene.Clear(0)

    def closeAllSegmentations(self):
        """Close all currently loaded segmentations"""
        segmentationNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        for node in segmentationNodes:
            slicer.mrmlScene.RemoveNode(node)

    def loadSegmentation(self, segPath: Path) -> bool:
        """Load segmentation into Slicer"""        
        success = slicer.util.loadSegmentation(str(segPath))
        if not success:
            logging.error(f"Failed to load segmentation: {segPath}")
            return False
                
        # Set up layout
        layoutManager = slicer.app.layoutManager()
        layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        
        # Get the segmentation node
        segmentationNode = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")[0]
        
        # Create 3D visualization
        segmentationNode.CreateClosedSurfaceRepresentation()
        
        # Hide volume in 3D view but keep segmentations visible
        volumeNodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        if volumeNodes:
            # Turn off volume rendering
            volRenLogic = slicer.modules.volumerendering.logic()
            displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(volumeNodes[0])
            displayNode.SetVisibility(False)
            
            # Also turn off volume slice visibility in 3D
            volumeNodes[0].GetDisplayNode().SetVisibility3D(False)
        
        self.current_segmentation_path = segPath
        self.reload_metadata()
        
        # Convert to binary labelmap representation for 2D views
        segmentationNode.CreateBinaryLabelmapRepresentation()
        return True
    
    def saveModifiedSegmentation(self, segmentationNode, imagePath: Path, expertID: str, 
                               notes: str, modelType: str, original_segmentation_path: Path = None):
        """Save modified segmentation and update metadata"""
        # Generate unique key and file hash
        timestamp_has = datetime.datetime.now()
        timestamp = timestamp_has.strftime("%Y%m%d_%H%M%S")
        fileHash = self._generateFileHash(segmentationNode, timestamp_has)
        imageID = imagePath.stem.split('-')[0]  # Get ID
        uniqueKey = f"{imageID}_{modelType}_{fileHash}_{timestamp}"

        # Create output path in ExpertAnnotations
        outputPath = self.dataset.paths['ExpertAnnotations'] / imageID /f"{imageID}_expert_{expertID}_{timestamp}.nii.gz"
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to binary labelmap for saving
        if not segmentationNode.GetSegmentation().GetNumberOfSegments():
            raise ValueError("No segments found in segmentation")
            
        # Create a new volume node for the binary labelmap
        labelmapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(segmentationNode, labelmapNode)
        
        # Save the labelmap
        slicer.util.saveNode(labelmapNode, str(outputPath))
        
        # Clean up temporary node
        slicer.mrmlScene.RemoveNode(labelmapNode)

        # Update metadata
        self._updateMetadata(outputPath, uniqueKey, imageID, expertID, notes, modelType, original_segmentation_path)

    def _updateMetadata(self, filepath: Path, uniqueKey: str, imageID: str, 
                        expertID: str, notes: str, modelType: str, original_segmentation_path: Path = None):
            """Update metadata file with new segmentation information."""
            metadataPath = self.dataset.base_path / 'metadata' / f"{modelType}_expert_metadata.json"
            
            # Get the original segmentation path
            if original_segmentation_path is None:
                try:
                    print(self.base_path)
                    assert()
                    imagePath = self.base_path / 'IXI_TOT' / f"{imageID}-Guys-0701-MRA.nii.gz"
                    original_seg_path = self.dataset.get_model_path(imagePath, modelType)
                except FileNotFoundError:
                    original_seg_path = None
            else:
                original_seg_path = original_segmentation_path
            
            # Create metadata entry
            metadata = {
                "unique_key": uniqueKey,
                "path": str(filepath),
                "relative_path": str(filepath.relative_to(self.base_path)),
                "filename": filepath.name,
                "image_id": imageID,
                "owner": expertID,
                "model": modelType,
                "original_segmentation_path": str(original_seg_path) if original_seg_path else None,
                "creation_date": datetime.datetime.now().isoformat(),
                "notes": notes,
                "size_bytes": filepath.stat().st_size,
                "file_hash": uniqueKey.split('_')[2]
            }

            # Load existing metadata
            if metadataPath.exists():
                with open(metadataPath, 'r') as f:
                    existing_metadata = json.load(f)
            else:
                existing_metadata = {}

            # Update metadata
            existing_metadata[uniqueKey] = metadata

            # Save updated metadata
            metadataPath.parent.mkdir(parents=True, exist_ok=True)
            with open(metadataPath, 'w') as f:
                json.dump(existing_metadata, f, indent=2)
    
    def getMetadata(self, segPath: Path) -> Dict:
        """Get metadata for a specific segmentation."""
        segPath = Path(segPath)
        print(f"Seg path: {segPath}")
        self.model_metadata = self._load_model_metadata()
        self.expert_metadata = self._load_expert_metadata()
        self.expert_VAL_metadata = self._load_expert_metadata(VAL=True)
        
        # Search for metadata entry
        entry_info = self._find_complete_metadata_entry(segPath)
        print(f"Entry info: {entry_info}")
        
        if not entry_info:
            return {}
        
        return entry_info 
        
    def _generateFileHash(self, node, timestamp: str = None) -> str:
        """Generate hash for the segmentation node"""
        if not timestamp:
            timestamp = str(datetime.datetime.now())
        else:
            timestamp = str(timestamp) 
        return hashlib.md5((timestamp).encode()).hexdigest()[:12]

    def track_history(self, seg_path: str) -> List[Dict]:
        """Track the history of a specific segmentation."""
        history = []
        
        current_path = Path(seg_path)
        
        print(f"Current path: {current_path}")

        if not current_path.exists():
            print(f"Error: File does not exist: {current_path}")
            return []
        
        # Track history recursively
        visited_paths = set()  # Prevent infinite loops
        while str(current_path) not in visited_paths:
            print(f"Current path HISTORY: {current_path}")
            visited_paths.add(str(current_path))
            
            entry_info = self._find_metadata_entry(current_path)
            if not entry_info:
                print(f"Error: Metadata not found for {current_path}")
                break
            entry_type, model_name, key, entry = entry_info
            history_entry = {
                'path': str(current_path),
                'type': entry_type,
                'model': model_name,
                'owner': entry.get('owner', 'Unknown'),
                'creation_date': entry.get('creation_date', 'Unknown'),
                'notes': entry.get('notes', '')
            }
            history.append(history_entry)
            
            # Check for original segmentation
            orig_path = entry.get('original_segmentation_path')
            if not orig_path:
                print(f"You reached the end of the history")
                break
            
            orig_path = get_relative_from_data(orig_path)
            orig_path = self.base_path / orig_path
            current_path = Path(orig_path)
            print(f"NEW Current path: {current_path}")
            if not current_path.exists():
                assert(), f"Error: Original segmentation not found: {current_path}"
                break
            if str(current_path) in visited_paths:
                print(f"Error: Infinite loop detected: {current_path}")
                break
                
        
        return history

    def _find_complete_metadata_entry(self, seg_path: Path) -> Optional[Dict]:
        flag = False
        for model_name, model_data in self.expert_metadata.items():
            for key, entry in model_data.items():
                if entry['relative_path'] == str(seg_path.relative_to(self.base_path)) or entry['path'] == str(seg_path):
                    print(f"Found expert metadata for {seg_path}")
                    flag = True
                    return entry
        if not flag:
            for model_name, model_data in self.expert_VAL_metadata.items():
                for key, entry in model_data.items():
                    if entry['relative_path'] == str(seg_path.relative_to(self.base_path)) or entry['path'] == str(seg_path):
                        print(f"Found expert metadata for {seg_path}")
                        flag = True
                        return entry

        if not flag:
            print("No expert metadata found: searching in model metadata")
            # print(f"Seg path: {seg_path}")
            for model_name, model_data in self.model_metadata.items():
                if model_name != Path(seg_path).parent.parent.stem:
                    continue
                # print(f"Model name: {model_name}")
                for key, entry in model_data.items():
                    # print(f"Key: {key}")
                    # print(f"Entry: {entry}")
                    if str(seg_path).endswith(entry['relative_path']):
                        # print(f"Found model metadata for {seg_path}")
                        return entry
            
    
    def _find_metadata_entry(self, seg_path: Path) -> Optional[tuple]:
        """Find metadata entry for a given segmentation path."""
        try:
            rel_path = str(seg_path.relative_to(self.base_path))
        except ValueError:
            rel_path = str(seg_path)
        
        # Search in expert metadata (for modifications)
        if 'ExpertAnnotations/' in rel_path:    
            for model_name, model_data in self.expert_metadata.items():
                for key, entry in model_data.items():
                    if entry['relative_path'] == rel_path or entry['path'] == str(seg_path):
                        return ('expert', model_name, key, entry)
        elif 'ExpertVAL/' in rel_path:
            # Search in VALIDATED expert metadata
            for model_name, model_data in self.expert_VAL_metadata.items():
                for key, entry in model_data.items():
                    if entry['relative_path'] == rel_path or entry['path'] == str(seg_path):
                        return ('expert', model_name, key, entry)
        else:
            # Search in model metadata (for originals)
            path_name = seg_path.name
            seg_model = seg_path.parent.parent.stem
            for model_name, model_data in self.model_metadata.items():
                if model_name in ['IXI_TOT','COW_TOT']:
                    continue
                if seg_model != model_name:
                    continue
                for key, entry in model_data.items():
                    if ((entry['relative_path'] == rel_path or 
                        entry['path'] == str(seg_path) or 
                        entry['filename'] == path_name)
                        ):
                        return ('model', model_name, key, entry)
                        
            return None

def get_relative_from_data(full_path: str, include_data: bool = False) -> str:
    """
    Extracts the subpath starting from 'data/' in the given absolute path.

    Parameters:
    full_path (str): The absolute file path.
    include_data (bool): Whether to include 'data/' in the returned path.

    Returns:
    str: The relative path starting from 'data/' (or without it if include_data=False), 
         or the original path if 'data/' is not found.
    """
    path_str = str(Path(full_path).resolve())  # Ensure it's a proper path string
    split_path = path_str.split("/data/", 1)

    if len(split_path) > 1:
        return ("data/" if include_data else "") + split_path[1]
    return path_str
    
class VesselVerseTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_VesselVerse1()

    def test_VesselVerse1(self):
        self.delayDisplay("Starting the test")
        # Add actual tests here
        self.delayDisplay('Test passed')
        
        
#######################################################################################
#######################################################################################
###### This code must be the same as the one in  vesselverse/src/core/dataset.py ######
#######################################################################################
#######################################################################################
import os
from typing import Dict, List

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from model_config.model_config import model_registry as registry

class Dataset:
    def __init__(self, base_path: str):
        from model_config.model_config import dataset_registry, model_registry  # Import registries

        self.base_path = Path(base_path).resolve()  # Convert to absolute path
        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {self.base_path}")

        # Retrieve dataset configuration based on base_path
        dataset_config = next((d for d in dataset_registry.datasets.values() if d.base_path.resolve() == self.base_path), None)

        if not dataset_config:
            raise ValueError(f"No dataset found for base path: {self.base_path}")

        # Load only supported models
        self.paths = {
            model_name: (self.base_path / model_name).resolve()  # Ensure absolute paths
            for model_name in dataset_config.supported_models if model_name in model_registry.models
        }

        # Create directories if they don't exist
        for path in self.paths.values():
            print(f"LOADING PATH: {path}")
            path.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, ixi_path: Path, model_name: str) -> Path:
        """Get path for model segmentation file.
        
        Args:
            ixi_path: Path to original IXI image
            model_name: Name of model ('STAPLE' or other model types)
            
        Returns:
            Path to segmentation file
            
        Raises:
            ValueError: If model_name is unknown
            FileNotFoundError: If segmentation file doesn't exist
        """
        model_config = registry.get_model(model_name)
        if not model_config:
            raise ValueError(f'Unknown model: {model_name}')
            
        
        try:
            TOT = [path for path in self.paths if path.endswith('_TOT')][0]
            rel_path = ixi_path.relative_to(self.paths[TOT])
        except ValueError:
            rel_path = Path(ixi_path.name)
            
        
        model_path = self.paths[model_name] / rel_path
        
        # Process filename if needed (e.g., change extension or prefix/suffix)
        if model_config.filename_processor:
            model_path = model_config.filename_processor(model_path)

        if not model_path.exists():
            raise FileNotFoundError(f'{model_name} segmentation not found: {model_path}')
        return model_path

def compareSegmentations(current_node, comparison_node, use_padding=False):
    """Create differential visualization showing unique areas of each segmentation.
    
    Args:
        current_node: First segmentation node (shown in green)
        comparison_node: Second segmentation node (shown in red) 
        use_padding: If True, uses binary dilation for tolerant overlap detection
    """
    resultNode = slicer.vtkMRMLSegmentationNode()
    slicer.mrmlScene.AddNode(resultNode)
    resultNode.CreateDefaultDisplayNodes()
    resultNode.CreateClosedSurfaceRepresentation()

    colorMap = {
        "Current         :": [0.0, 1.0, 0.0],     # Green
        "Comparison  :": [1.0, 0.0, 0.0],     # Red
        "Overlap        :": [1.0, 1.0, 0.0]      # Yellow
    }

    segmentIDs = {}
    displayNode = resultNode.GetDisplayNode()
    displayNode.SetAllSegmentsVisibility2DFill(True)
    displayNode.SetAllSegmentsVisibility2DOutline(True)

    for name in colorMap:
        segID = resultNode.GetSegmentation().AddEmptySegment(name)
        segmentIDs[name] = segID
        segment = resultNode.GetSegmentation().GetSegment(segID)
        if segment:
            segment.SetColor(*colorMap[name])
            displayNode.SetSegmentOpacity3D(segID, 1.0)
            displayNode.SetSegmentOpacity2DFill(segID, 1.0)
            displayNode.SetSegmentOpacity2DOutline(segID, 1.0)

    reference_volume = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not reference_volume:
        raise RuntimeError("A valid reference volume is required.")

    # Get labelmap representations
    current_labelmap = slicer.util.arrayFromSegmentBinaryLabelmap(
        current_node, current_node.GetSegmentation().GetNthSegmentID(0), reference_volume)
    comparison_labelmap = slicer.util.arrayFromSegmentBinaryLabelmap(
        comparison_node, comparison_node.GetSegmentation().GetNthSegmentID(0), reference_volume)

    if use_padding:
        from scipy.ndimage import binary_dilation
        padding = 1
        current_padded = binary_dilation(current_labelmap, iterations=padding)
        comparison_padded = binary_dilation(comparison_labelmap, iterations=padding)
        overlap_labelmap = (current_padded & comparison_padded).astype(current_labelmap.dtype)
        current_only = (current_padded & ~overlap_labelmap).astype(current_labelmap.dtype)
        comparison_only = (comparison_padded & ~overlap_labelmap).astype(comparison_labelmap.dtype)
    else:
        overlap_labelmap = (current_labelmap & comparison_labelmap).astype(current_labelmap.dtype)
        current_only = (current_labelmap & ~overlap_labelmap).astype(current_labelmap.dtype)
        comparison_only = (comparison_labelmap & ~overlap_labelmap).astype(comparison_labelmap.dtype)

    # Update all segments
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        current_only, resultNode, segmentIDs["Current         :"], reference_volume)
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        comparison_only, resultNode, segmentIDs["Comparison  :"], reference_volume)
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        overlap_labelmap, resultNode, segmentIDs["Overlap        :"], reference_volume)

    resultNode.CreateClosedSurfaceRepresentation()
    displayNode.SetVisibility3D(True)

    return resultNode

def resolve_and_fix_path(relative_path: str, reference_path: str) -> Path:
    """
    Resolves a relative path using a reference absolute path and 
    automatically fixes duplicated directory structures.
    
    :param relative_path: The relative path to resolve
    :param reference_path: A reference absolute path to determine the correct base
    :return: Corrected absolute Path object
    """
    # Resolve relative path against the reference's parent directory
    reference_parent = Path(reference_path).parent
    resolved_path = (reference_parent / Path(relative_path)).resolve()

    # Convert to string for manipulation
    corrected_str = str(resolved_path)

    # Dynamically detect and fix duplicate directory structures
    path_parts = corrected_str.split('/')
    seen = set()
    corrected_parts = []

    for part in path_parts:
        if part in seen:
            # If a duplicate segment is detected, skip it
            continue
        seen.add(part)
        corrected_parts.append(part)

    corrected_path = Path('/'.join(corrected_parts))

    return corrected_path
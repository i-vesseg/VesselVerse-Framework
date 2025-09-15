import qt, slicer
from slicer.ScriptedLoadableModule import *

class opacity_slicer(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Opacity Controls"
        self.parent.categories = ["Utilities"]
        self.parent.contributors = ["Daniele Falcetta (EURECOM - Biot, France)"]
        
class opacity_slicerWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

class SegmentControl(qt.QWidget):
    def __init__(self, segmentID, name, parent=None):
        super().__init__(parent)
        layout = qt.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create checkbox with colored box
        self.checkbox = qt.QCheckBox(name)
        self.checkbox.setChecked(True)
        message_dict = {
            "Current         :": "Show/Hide Exclusive Vessels in Current Segmentation Version",
            "Comparison  :": "Show/Hide Exclusive Vessels in Comparison Segmentation Version",
            "Overlap        :": "Show/Hide Overlapping Vessels in Both Segmentation Versions",
            "Segmentation :": "Show/Hide Loaded Segmentation",
            "Segmentation Editor :": "Show/Hide Segmentation in Editor Mode "
        }
        self.checkbox.setToolTip(f"{message_dict[name]}")
        
        # Set color based on segment name
        color_map = {
            "Current         :": "#00FF00",  # Green
            "Comparison  :": "#FF0000",  # Red 
            "Overlap        :": "#FFFF00",   # Yellow
            "Segmentation :": "#89CFF0",  # Light blue
            "Segmentation Editor :": "#00FF00"  # Green
        }
        if name in color_map:
            colorBox = qt.QFrame()
            colorBox.setFixedSize(16, 16)
            colorBox.setStyleSheet(f"background-color: {color_map[name]}; border: 1px solid #999999;")
        else:
            print(f"Warning: No color defined for segment '{name}'")
            colorBox = qt.QLabel()
            colorBox.setFixedSize(16, 16)
            colorBox.setStyleSheet(f"background-color: Generic Segmentation; border: 1px solid #999999;")
        layout.addWidget(colorBox)
        layout.addWidget(self.checkbox)
        
        
        
        self.slider = qt.QSlider(qt.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(100)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #E0E0E0;
                margin: 1px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.slider)
        
        self.opacityLabel = qt.QLabel("100%")
        self.opacityLabel.setFixedWidth(40)
        layout.addWidget(self.opacityLabel)
        
        self.segmentID = segmentID
        self.slider.valueChanged.connect(self._updateOpacityLabel)
        
    def _updateOpacityLabel(self, value):
        self.opacityLabel.setText(f"{value}%")

class OpacitySliderWidget(qt.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = qt.QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Header
        headerLabel = qt.QLabel("Segment Controls")
        headerLabel.setStyleSheet("font-weight: bold;")
        layout.addWidget(headerLabel)
        
        # Container for segment controls
        self.controlsContainer = qt.QWidget()
        self.controlsLayout = qt.QVBoxLayout(self.controlsContainer)
        self.controlsLayout.setSpacing(4)
        self.controlsLayout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.controlsContainer)
        
        self.segmentControls = {}
        
    def updateForNode(self, node):
        """Update controls for specific node."""
        # Clear existing controls
        for control in self.segmentControls.values():
            self.controlsLayout.removeWidget(control)
            control.deleteLater()
        self.segmentControls.clear()
        
        if not node:
            return
            
        # Create controls for each segment
        for i in range(node.GetSegmentation().GetNumberOfSegments()):
            segID = node.GetSegmentation().GetNthSegmentID(i)
            name = node.GetSegmentation().GetSegment(segID).GetName()
            
            control = SegmentControl(segID, name)
            self.segmentControls[segID] = control
            self.controlsLayout.addWidget(control)
            
            # Connect signals
            control.checkbox.stateChanged.connect(
                lambda state, sid=segID: self._updateSegmentVisibility(sid, state))
            control.slider.valueChanged.connect(
                lambda value, sid=segID: self._updateSegmentOpacity(sid, value))
            
    def _updateSegmentVisibility(self, segmentID, state):
        """Update visibility for segment."""
        nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        for node in nodes:
            displayNode = node.GetDisplayNode()
            if displayNode and node.GetSegmentation().GetSegment(segmentID):
                isVisible = state == qt.Qt.Checked
                displayNode.SetSegmentVisibility(segmentID, isVisible)
                displayNode.SetSegmentVisibility3D(segmentID, isVisible)
                displayNode.SetSegmentVisibility2DFill(segmentID, isVisible)
                displayNode.SetSegmentVisibility2DOutline(segmentID, isVisible)
    
    def _updateSegmentOpacity(self, segmentID, value):
        """Update opacity for segment."""
        opacity = value / 100.0
        nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        for node in nodes:
            displayNode = node.GetDisplayNode()
            if displayNode and node.GetSegmentation().GetSegment(segmentID):
                displayNode.SetSegmentOpacity3D(segmentID, opacity)
                displayNode.SetSegmentOpacity2DFill(segmentID, opacity)
                displayNode.SetSegmentOpacity2DOutline(segmentID, opacity)
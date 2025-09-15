cmake_minimum_required(VERSION 3.13.4)

project(VesselVerse)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/VesselVerse")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Daniele Falcetta (EURECOM - Biot, France)")
set(EXTENSION_DESCRIPTION "VesselVerse extension for vessel segmentation management and version tracking")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/VesselVerse.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/VesselVerse/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list of dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
set(MODULE_NAME "VesselVerse")
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/icon_V.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
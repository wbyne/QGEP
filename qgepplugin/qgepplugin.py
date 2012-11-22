# -*- coding: utf-8 -*-
#-----------------------------------------------------------
#
# Profile
# Copyright (C) 2012  Matthias Kuhn
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from tools.qgepmaptools import QgepProfileMapTool, QgepTreeMapTool
from tools.qgepnetwork import QgepNetworkAnalyzer
from ui.qgepdockwidget import QgepDockWidget
from ui.qgepplotsvgwidget import QgepPlotSVGWidget
import resources

class QgepPlugin:
    # The networkAnalyzer will manage the networklayers and pathfinding
    networkAnalyzer = None
    
    # Remember not to reopen the dock if there's already one opened
    dockWidget      = None

    #===============================================================================
    # Constructor
    #===============================================================================
    def __init__( self, iface ):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        
    #=======================================================================
    # Called to setup the plugin GUI
    #=======================================================================
    def initGui( self ):
        self.toolbarButtons = []
        
        # Create toolbar button
        self.profileAction = QAction( QIcon( ":/plugins/qgepplugin/icons/wastewater-profile.svg" ), "Profile", self.iface.mainWindow() )
        self.profileAction.setWhatsThis( "Reach trace." )
        self.profileAction.setEnabled( False )
        self.profileAction.setCheckable( True )
        self.profileAction.triggered.connect( self.profileToolClicked )

        self.downstreamAction = QAction( QIcon( ":/plugins/qgepplugin/icons/wastewater-downstream.svg" ), "Downstream", self.iface.mainWindow() )
        self.downstreamAction.setWhatsThis( "Downstream reaches" )
        self.downstreamAction.setEnabled( False )
        self.downstreamAction.setCheckable( True )
        self.downstreamAction.triggered.connect( self.downstreamToolClicked )

        self.upstreamAction = QAction( QIcon( ":/plugins/qgepplugin/icons/wastewater-upstream.svg" ), "Upstream", self.iface.mainWindow() )
        self.upstreamAction.setWhatsThis( "Upstream reaches" )
        self.upstreamAction.setEnabled( False )
        self.upstreamAction.setCheckable( True )
        self.upstreamAction.triggered.connect( self.upstreamToolClicked )
        
        self.aboutAction = QAction( "About", self.iface.mainWindow() )
        self.aboutAction.triggered.connect( self.about )

        # Add toolbar button and menu item
        self.iface.addToolBarIcon( self.profileAction )
        self.iface.addToolBarIcon( self.upstreamAction )
        self.iface.addToolBarIcon( self.downstreamAction )

        self.iface.addPluginToMenu( "&QGEP", self.profileAction )
        self.iface.addPluginToMenu( "&QGEP", self.aboutAction )
        
        # Local array of buttons to enable / disable based on context
        self.toolbarButtons.append( self.profileAction )
        self.toolbarButtons.append( self.upstreamAction )
        self.toolbarButtons.append( self.downstreamAction )
        
        # Init the object maintaining the network
        self.networkAnalyzer = QgepNetworkAnalyzer( self.iface )
        # Create the map tool for profile selection
        self.profileTool = QgepProfileMapTool( self.canvas, self.profileAction, self.networkAnalyzer )
        self.profileTool.profileChanged.connect( self.onProfileChanged )
        
        self.upstreamTreeTool = QgepTreeMapTool( self.canvas, self.upstreamAction, self.networkAnalyzer )
        self.upstreamTreeTool.setDirection( "upstream" )
        self.downstreamTreeTool = QgepTreeMapTool( self.canvas, self.downstreamAction, self.networkAnalyzer )
        self.downstreamTreeTool.setDirection( "downstream" )
        
        # Connect to events that can change layers
        QgsMapLayerRegistry.instance().layersWillBeRemoved.connect( self.layersWillBeRemoved )
        QgsMapLayerRegistry.instance().layersAdded.connect( self.layersAdded )
        
    #===========================================================================
    # Called when unloading
    #===========================================================================
    def unload( self ):
        self.iface.removeToolBarIcon( self.profileAction )
        self.iface.removeToolBarIcon( self.upstreamAction )
        self.iface.removeToolBarIcon( self.downstreamAction )
        self.iface.removePluginMenu( "&QGEP", self.profileAction )
        self.iface.removePluginMenu( "&QGEP", self.aboutAction )

    #===========================================================================
    # Is executed when the profile button is clicked
    #===========================================================================
    def profileToolClicked( self ):
        self.openDock()
        # Set the profile map tool
        self.profileTool.setActive()
    
    #=======================================================================
    # Is executed when the user clicks the upstream search tool
    #=======================================================================
    def upstreamToolClicked(self):
        self.upstreamTreeTool.setActive()
        
    #===========================================================================
    # Is executed when the user clicks the downstream search tool
    #===========================================================================
    def downstreamToolClicked(self):
        self.downstreamTreeTool.setActive()

    #===========================================================================
    # Opens the dock
    #===========================================================================
    def openDock(self):
        if self.dockWidget is None:
            self.dockWidget = QgepDockWidget( self.iface.mainWindow(), self.iface )
            self.dockWidget.closed.connect( self.onDialogClosed )
            self.dockWidget.showIt()
            
            self.plotWidget = QgepPlotSVGWidget( self.dockWidget, self.networkAnalyzer )
            self.dockWidget.addPlotWidget( self.plotWidget )

    
    #===========================================================================
    # Gets called when a layer is removed    
    #===========================================================================
    def layersWillBeRemoved( self, layerList ):
        for layerId in layerList:
            if 0!= self.networkAnalyzer.getNodeLayer():
                if self.networkAnalyzer.getNodeLayerId() == layerId:
                    self.networkAnalyzer.setNodeLayer( 0 )
                    self.layersChanged()
                
            if 0!= self.networkAnalyzer.getReachLayer(): 
                if self.networkAnalyzer.getReachLayerId() == layerId:
                    self.networkAnalyzer.setReachLayer( 0 )
                    self.layersChanged()
                    
    #===========================================================================
    # Gets called when a layer is added
    #===========================================================================
    def layersAdded( self, layers ):
        for newLayer in layers:
            if newLayer.type() == QgsMapLayer.VectorLayer and newLayer.name() == "vw_network_node":
                self.networkAnalyzer.setNodeLayer( newLayer )
                self.layersChanged()

            if newLayer.type() == QgsMapLayer.VectorLayer and newLayer.name() == "vw_network_segment":
                self.networkAnalyzer.setReachLayer( newLayer )
                self.layersChanged()
                
    #===========================================================================
    # Gets called when the layers have changed
    #===========================================================================
    def layersChanged( self ):
        buttonsEnabled = False
        
        if self.networkAnalyzer.getNodeLayer() and self.networkAnalyzer.getReachLayer():
            buttonsEnabled = True
            
        for button in self.toolbarButtons:
            button.setEnabled( buttonsEnabled )
    
    #===========================================================================
    # The profile changed: update the plot
    #===========================================================================
    
    def onProfileChanged( self, profile ):
        if self.plotWidget:
            self.plotWidget.setProfile( profile )

    
    def onDialogClosed( self ):        #used when Dock dialog is closed
        self.dockWidget = None

    def about( self ):
        from ui.dlgabout import DlgAbout
        DlgAbout( self.iface.mainWindow() ).exec_()

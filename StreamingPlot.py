#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implementation of interactive plotting of streaming tweets word analysis in 
Jupyter Notebook.

Author: Xian Lai
Date: Nov.30, 2017
"""

import numpy as np
import time

from bokeh.layouts import widgetbox, row
from bokeh.palettes import Spectral11, RdYlGn11
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.io import output_notebook, show, push_notebook
output_notebook()

sm_font = {'fontsize':13, 'fontname':'Arial'}
md_font = {'fontsize':15, 'fontname':'Arial', 'fontweight':'bold'}
lg_font = {'fontsize':17, 'fontname':'Arial', 'fontweight':'bold'}
grey    = {'light':'#efefef', 'median':'#aaaaaa', 'dark':'#282828'}
cms     = {'Spectral':Spectral11, 'RdYlGn':RdYlGn11}

class StreamingPlot():

    """
    This defines a streaming plotting object that keep updating with given time
    interval. 
    """

    def __init__(self, interval=5, width=900, height=900):
        """ Init the StreamingPlot object with settings and an empty dict. 
        
        Inputs:
        -------
        - interval: the inverval of refreshing plot
        - width, height: the width and height of figure

        We will send in the streaming data by updating the data attribute. The
        data should be in form of a dict:
        {
         'x' : the conditional probability of feature word given label "maga",
         'y' : the conditional probability of feature word given label "resist", 
         'text' : the feature word, 
         'color' : the labels of this feature word, 
         'size' : the informativeness of this feature word]
         'tags' : the legends of plotting
        }
        """
        self.width  = width
        self.height = height
        self.itv    = interval
        self.data   = {'x':[], 'y':[], 'color':[], 'alpha':[], 
                       'tags':[], 'size':[]}
        self.ds     = ColumnDataSource(data=self.data)
        self._makeFig()


    def _setFig(self):
        """ set attributes of given bokeh fig
        """
        self.p.background_fill_color = grey['light']
        self.p.xgrid.grid_line_color = None
        self.p.ygrid.grid_line_color = None
        self.p.ygrid.grid_line_dash  = 'dotted'
        self.p.ygrid.grid_line_dash  = 'dotted'

        self.p.xgrid.minor_grid_line_color = grey['median']
        self.p.ygrid.minor_grid_line_color = grey['median']
        self.p.xgrid.minor_grid_line_dash  = 'dotted'
        self.p.ygrid.minor_grid_line_dash  = 'dotted'

        self.p.xaxis.axis_label = "tsne_feature_0"
        self.p.yaxis.axis_label = "tsne_feature_1"


    def _makeFig(self):
        """
        parameters for circle plot:
        ---------------------------
        - x: x-coordinates
        - y: y-coordinates
        - radius: the radius for circle markers
        - fill_alpha[1.0]: The fill alpha values for the markers
        - fill_color['grey']: The fill color values for the markers.
        - line_alpha[1.0]: The line alpha values for the markers.
        - line_color['black']: The line color values for the markers.
        - line_width[1]: The line width values for the markers.
        """
        self.p  = figure(
            plot_width=self.width, plot_height=self.height, 
            title='Streaming text analysis', 
            tools='pan, wheel_zoom, reset, save'
        )
        self._setFig()

        self.r  = self.p.circle(
            x='x', y='y', radius='size', fill_color='color', 
            fill_alpha='alpha', legend='tags', line_alpha=0, source=self.ds
        )


    def start(self, data):
        """ start the streaming plotting.
        """
        # show the plotting and leave a handle
        handle = show(self.p, notebook_handle=True)
        
        # keep update the column data source with new data and push the 
        # updating onto Jupyter notebook.
        while True:
            try: self.ds.stream(data, rollover=300)
            except ValueError: return
            push_notebook(handle=handle)
            time.sleep(self.itv)



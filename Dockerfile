# Distributed under the terms of the Modified BSD License.

# This image is almost identical to the parent image living at
# https://github.com/jupyter/docker-stacks/tree/master/pyspark-notebook
# except it installs tweepy and bokeh libraries.

# pull the parent image
FROM jupyter/pyspark-notebook

# this image is used for 
LABEL project="Streaming analysis and visualization"

# install Python library tweepy
RUN pip install tweepy

# install Python library bokeh
RUN pip install bokeh


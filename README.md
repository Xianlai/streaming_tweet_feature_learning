# Streaming Tweets Feature Learning with Spark

## Synopsis
![](imgs/logos.png)
#### As the diagram showing above, this project implements a pipeline that learns predictive features from streaming tweets and visualizes the result in real-time:

- **Receive streaming tweets on master machine**:    
    Running the TweetsListener.py script in the background, a tweets stream with 3 tracks-"NBA", "NFL" and "MBL" are pulled from Tweepy API. Inside this stream, each tweet has a topic about one of those 3 tracks and is seperated by delimiter "><". 

        example raw tweets:  
        Here's every Tom Brady Postseason TD! #tbt #NFLPlayoffs https://t.co/2CIHBpz2OW...  
        RT @ChargersRHenne: This guy seems like a class act.  I will root for him  
        RT @NBA: Kyrie ready! #Celtics #NBALondon https://t.co/KgZVsREGUK...  
        RT @NBA: The Second @NBAAllStar Voting Returns! https://t.co/urTwnGQNKl...  
        ...  

- **Analysis tweets on distributed machines**:    
    This stream is directed into Spark Streaming API through TCP connection and distributed onto cluster. Under the Spark Streaming API, the distrbuted stream is abstracted as a data type called DStream. A series of operations are then applied on this DStream in real time and transform it into other DStreams containing intermediate or final analysis results. 
    
    1. preprocess each tweet into a label and a list of clean words which contains only numbers and alphabets.
    
        example cleaned tweets after preprocessing:
        tag:1, words:['rt', 'chargersrhenne', 'this', 'guy', ...],    
        tag:0, words:['rt', 'debruynekev', 'amp', 'ilkayguendogan', ...],    
        tag:0, words:['rt', 'commissioner', 'adam', 'silver', ...],    
        tag:0, words:['rt', 'spurs', 'all', 'star', ...],    
        tag:0, words:['nbaallstar', 'karlanthony', 'towns', 'nbavote', ...],   
        ...    

    2. count the frequencies of words in all tweets and take the top 5000 most frequent ones as features.
    
        example word count:  
        ('rt' , 196)  
        ('the', 174)  
        ('in' , 85)  
        ('for', 62)  
        ('to' , 59)  
        ...

    3. encode the tweets in last 15 seconds into a structured dataset using features mentioned above.
    
        example encoded dataset:  
        tag: 0, features: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...],  
        tag: 1, features: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...],  
        tag: 2, features: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...],  
        tag: 0, features: [0, 1, 1, 1, 1, 1, 0, 0, 0, 0, ...],  
        tag: 1, features: [0, 0, 1, 0, 0, 0, 1, 1, 1, 1, ...],  
        ...  

    4. calculate the conditional probability given label and the predictiveness of each feature word.
    
        most predictive word : (cp0, cp1, cp2, pdtn)  
        allstar     : (0.14835164835164835, 0.0078125, 0.05555555555555555, 249.3439)  
        alabama     : (0.005494505494505495, 0.140625, 0.05555555555555555, 216.67129)  
        fitzpatrick : (0.005494505494505495, 0.1328125, 0.05555555555555555, 195.5925333333333)  
        voting      : (0.12637362637362637, 0.0078125, 0.05555555555555555, 187.45217333333335)  
        minkah      : (0.005494505494505495, 0.125, 0.05555555555555555, 175.55554999999998)  
        draft       : (0.016483516483516484, 0.171875, 0.1111111111111111, 149.7176)  
        ...  
    
- **Visualize results on master machine**:   
    At last we select the tweets and features with higher predictiveness, collect their label, sum of predictiveness and 2 tsne features back onto the master machine and visualize them as a scatter plot. 

    1. keep only 300 most predictive features and discard other non-predictive features.
    2. calculate the sum of predictiveness of each word in tweet.
    3. take 60 tweets with the highest sum of predictiveness under each label.
    4. apply TSNE learning on these 300 data points to reduce dimentionality from 100 to 2 for visualization.
    
    This visualization can be used as an informal way to validate the predictiveness defined above. If the scatter circles of different labels are well seperated, then the features selected by this predictiveness measure are working well.
    
    ![](imgs/tweet_feature_learning.gif)


## Files
- **tweet_feature_learning_SparkStreaming.ipynb**
    This jupyter notebook contains the code receiving tweets from socket, learn features and their stats and visualize selected tweets using learned features.
- **TweetsListener.py**
    This python script pulls realtime tweets from tweepy API and forward it to the assigned TCP connect.(If you are not using docker container, you need to modify the IPaddress information in this file as well as in tweet_feature_learning_SparkStreaming.ipynb to make the streaming work.)
- **StreamingPlot.py**
    This python script implements the streaming plotting class which generate a scatter plotting and keeps updating the plotting with new plotting data source.
- **pyspark_installation_guide.md**
    This markdown file contains guided steps on how to install Spark and pyspark.
- **Spark_overview.md**
    This markdown file briefly introduces what is Spark and the functionalities of it.
- **logs.txt**
    This text file is generated in tweet_feature_learning_SparkStreaming.ipynb to save intermediate and final analysis result.


## To run the notebook:
The Jupyter notebooks and scripts are implemented and working in docker container run from docker image `xianlai/spark_project`. 

1. In order to receive Tweets, you firstly need to add your own Twitter API keys in the [TweetsListener.py](./TweetsListener.py) file. The variables that need to be set are at the top as follows:
```python
consumer_key    = None  # Replace with your Consumer key
consumer_secret = None  # Replace with your Consumer secret
access_token    = None  # Replace with your acces token
access_secret   = None  # Replace with your access secret
```

2. Run the following command to start a container with the Notebook server listening for HTTP connections on port 8888. 

    ```bash
    docker run -it -v localDir:/home/jovyan -p 8888:8888 xianlai/spark_project
    ```

    Here `-v localDir:/home/jovyan` allows you to mount a local volume to container and the `localDir` is the directory where you downloaded the above files.

    Then you will see a notebook startup log messages like this:
    ```
    Copy/paste this URL into your browser when you connect for the first time,
    to login with a token:
        http://localhost:8888/?token=75b0b2062b7e8da090cc16d9581e3b9d98158903fcf8db36
    ```

    If you don't have docker installed, please refer to [pyspark_installation_guide.md](./pyspark_installation_guide.md) for installing guides.

3. Take note of the authentication token and include it in the URL you visit to access the Notebook server.

4. Open `tweet_feature_learning_SparkStreaming.ipynb` and run all cells.


## API Reference
- **Spark**: URL:http://spark.apache.org/
- **Tweepy** : URL:http://www.tweepy.org/
- **Bokeh**: Bokeh Development Team (2014). Bokeh: Python library for interactive visualization. URL:http://www.bokeh.pydata.org.


## License
MIT License

Copyright (c) [2017] [Xian Lai]

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contact
Xian Lai
Data Analytics, CIS @ Fordham University
XianLaaai@gmail.com

# Streaming Tweets Feature Learning with Spark
# 推特流数据实时特征学习(Spark Streaming)

### Xian Lai
### 赖献

xian_lai@126.com

=======================================================
![](imgs/tweet_feature_learning.gif)

## Abstract
## 概要
As the role of big data analysis playing in ecommerce becoming increasingly important, more and more streaming computation systems like Storm, Hadoop are developed trying to satisfy requirements of both time and space efficiency as well as accuracy. 

Among them, Spark Streaming is a great tool for mini-batch real-time streaming analysis running on distributed computing system. Under the Spark Streaming API, the data stream is distributed on many workers and abstracted as a data type called DStream. DStream is essentially a sequence of Resilient Distributed Datasets(RDDs). A series of operations can then applied on this sequence of RDD's in real-time and transform it into other DStreams containing intermediate or final analysis results.

In this project, a life tweets streaming are pulled from Tweeter API. 300 most predictive features words for hashtag classification are learned from this stream using Spark Streaming library in real-time. To validate the learning process, these 300 features are are reduced to a 2-d coordinate system. New tweets are plot on these 2 dimensions as scatter. As more and more tweets  learned by the system, the tweets with same hashtag gradualy aggregate together on this 2-d coordinates which means they are easily separable based on this features.

#### The reasons using Spark Streaming for this project are:
#### 使用Spark Streaming的原因：
1. Spark streaming handles the in-coming stream in small batches. It is very flexible for either incremental or recomputational calculations(In our case, the counts and predictiveness of feature words are updated incrementally on previous result and all others are recomputed from scratch every 5 seconds). 
2. Streaming computing and distributed computing are well intergrated thus the algorithm is scalable. 
3. We can easily apply other existing RDD operations under Spark framework like machine learning functions and SQL queries on the DStream. 
4. Although there are many other tools can handle streaming data in distributed machines, Spark's core abstraction RDD, which caches data in memory, saves time for data I/O from external storage system and thus makes iterative calculation much more efficient.

## Real-time Learning Pipeline
## 实时学习工作流
![](imgs/logos.png)

### I. Receive and clean streaming tweets:  
### I. 接收和清理推特数据流:

1. Running the [TweetsListener.py](https://github.com/Xianlai/streaming_tweet_feature_learning/blob/master/TweetsListener.py) script in the background, a tweets stream with any one of 3 tracks-"NBA", "NFL" and "MBL" are pulled from Tweeter API. 

    ```python
    >>> Input:
        # set up spark configuration using local mode with all CPU's
        # create a spark context with this configuration
        # create a streaming context and set the interval to 5 second.
        conf = SparkConf().setMaster("local[*]")
        sc   = SparkContext(conf=conf)
        ssc  = StreamingContext(sc, batchDuration=5)
        sc.setLogLevel("ERROR")
        ssc.checkpoint("checkpoint")

        # create a DStream by listening to socket
        # For each RDD in stream:
        # - split the tweets by delimiter "><"
        # - flat map all the rows contains list
        # get n rows, each row is a raw tweet: (tweet)
        rawTweets = ssc.socketTextStream('172.17.0.2',5555)\
            .map(lambda x: x.split("><"))\
            .flatMap(lambda x: x)\
    >>> Output:
        "
        Here's every Tom Brady Postseason TD! #tbt #NFLPlayoffs https://t.co/2CIHBpz2OW...  
        RT @ChargersRHenne: This guy seems like a class act.  I will root for him  
        RT @NBA: Kyrie ready! #Celtics #NBALondon https://t.co/KgZVsREGUK...  
        RT @NBA: The Second @NBAAllStar Voting Returns! https://t.co/urTwnGQNKl...  
        ...  
        "
    ```

2. Each tweet in the raw tweet stream is then been preprocessed into a label and a list of clean words containing only numbers and alphabets.

    ```python
    >>> Input:
        # For each RDD in stream:
        # - split the sentence
        # - strip the symbols and keep only numbers and alphabets
        # - lower case the words
        # - remove empty strings
        # - assign tags for each tweet and remove tag words
        # get n rows: (tag, [word_0, word_1, ..., word_m])
        cleanTweets = rawTweets\
            .map(lambda x: x.split())\
            .map(lambda xs: [sub('[^A-Za-z0-9]+', '', x) for x in xs])\
            .map(lambda xs: [x.lower() for x in xs])\
            .map(lambda xs: [x for x in xs if x != ''])\
            .map(assignTag)\
            .filter(lambda x: x != None)

    >>> Output:
        "
        tag:1, words:['rt', 'chargersrhenne', 'this', 'guy', ...],    
        tag:0, words:['rt', 'debruynekev', 'amp', 'ilkayguendogan', ...],    
        tag:0, words:['rt', 'commissioner', 'adam', 'silver', ...],    
        tag:0, words:['rt', 'spurs', 'all', 'star', ...],    
        tag:0, words:['nbaallstar', 'karlanthony', 'towns', 'nbavote', ...],   
        ... 
        "
    ```

3. we will split training and testing data set from clean tweets stream. One third of the tweets are preserved for future result validation. 

    ```python
    >>> Input:
        # For each RDD in stream:
        # n rows: (tag, [word_0, word_1, ..., word_m])
        # - zip with index: (index, (tag, [word_0, word_1, ..., word_m]))
        # - mod the index by 3: (index%3, (tag, [word_0, word_1, ..., word_m]))
        cleanTweets_mod = cleanTweets\
            .transform(lambda rdd: rdd.zipWithIndex())\
            .map(lambda x: (x[0] % 3, x[1]))

        # For each RDD in stream:
        # n rows: (index%3, (tag, [word_0, word_1, ..., word_m]))
        # - filter the rows with remainder equals to 0 or 1
        # - take the label and list of words: (tag, [word_0, word_1, ..., word_m])
        cleanTweets_train = cleanTweets_mod\
            .filter(lambda x: x[0] == 0 or 1)\
            .map(lambda x: x[1])

        # For each RDD in stream:
        # n rows: (index%3, (tag, [word_0, word_1, ..., word_m]))
        # - filter the rows with remainder equals to 2
        # - take the label and list of words: (tag, [word_0, word_1, ..., word_m])
        cleanTweets_test = cleanTweets_mod\
            .filter(lambda x: x[0] == 2)\
            .map(lambda x: x[1])
    ```

### II. Feature extraction:    
### II. 特征抽取: 
These words are counted and top 5000 most frequent words are collected as features for continue learning.    

```python
    >>> Input:
        # For each RDD in stream:
        # - remove the tag
        # - flatten the list of words so each row has one word
        # - add 1 count to each word
        # - use the new word count to update old word count dictionary incrementally
        # - sort the word and count tuple by the count in descending order
        # get n rows: (word, count)
        wordCount = cleanTweets_train\
            .map(lambda x: x[1])\
            .flatMap(lambda x: x)\
            .map(lambda x: (x, 1))\
            .updateStateByKey(updateWordCount)\
            .transform(lambda rdd: rdd.sortBy(lambda x: -x[1]))

        # For each RDD in stream:
        # - zip rows with index
        # - filter the first 5000 rows
        # - discard the index
        # get 5000 rows: (word, count)
        features = wordCount\
            .transform(lambda rdd: rdd.zipWithIndex())\
            .filter(lambda x: x[1] < 5000)\
            .map(lambda x: x[0])
    
        words = features.map(lambda x: x[0])
        counts = features.map(lambda x: x[1])

    >>> Output:
        "
        ('rt' , 196)  
        ('the', 174)  
        ('in' , 85)  
        ('for', 62)  
        ('to' , 59)  
        ...
        "
```


### III. Feature predictiveness learning
### III. 特征预测能力值测算: 
1. encode the cleaned tweets stream into a structured dataset using features mentioned above.

    ```python
    >>> Input:
        def encodeDataSet(rdd_a, rdd_b):
            """ Encode given tweets by given feature words.
            If a feature word appears in this tweet, the corresponding
            feature is 1, otherwise 0.
            """
            words_  = rdd_b.collect()
            rdd_new = rdd_a.mapValues(lambda x: \
                ([int(word in x) for word in words_], 1))
            return rdd_new

        # For each RDD in stream:
        # - get tweets in 15s window every 5s
        # - encoded the tweets using features and append value 1
        #   onto each tweet to count the number of tweets later.
        # get rows: (tag, ([1, 0, ..., 1], 1))
        dataset_train = cleanTweets_train\
            .transformWith(encodeDataSet, words)

    >>> Output:
        "
        tag: 0, features: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...],  
        tag: 1, features: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...],  
        tag: 2, features: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...],  
        tag: 0, features: [0, 1, 1, 1, 1, 1, 0, 0, 0, 0, ...],  
        tag: 1, features: [0, 0, 1, 0, 0, 0, 1, 1, 1, 1, ...],  
        ... 
        "
    ```

2. calculate the conditional probability given label and the predictiveness of each feature word.
     
    **p(feature|tag)**:   
    Since all the feature values are either 0 or 1, we can easily get the probability of one feature conditioned on any tag by counting the tweets containing this feature under corresponding tag and divide it by the total count of tweets under this tag.

    <a href="http://www.codecogs.com/eqnedit.php?latex=cp_0&space;=&space;\frac{count(feature=1,&space;tag=0)}{count(tag=0)}" target="_blank"><img src="http://latex.codecogs.com/gif.latex?cp_0&space;=&space;\frac{count(feature=1,&space;tag=0)}{count(tag=0)}" title="cp_0 = \frac{count(feature=1, tag=0)}{count(tag=0)}" /></a>


    **predictiveness**:  
    Then we calculate the predictiveness of each feature from this dataset. The predictiveness of one feature quantifies how well can a feature discriminate the label of a tweet from other 2 labels.

    1. If we have only 2 labels, it can be defined by the bigger ratio of conditional probabilities of this feature given tags.
        
        <a href="http://www.codecogs.com/eqnedit.php?latex=pdtn(label_1,&space;label_2)&space;=&space;arg&space;max\left(&space;\frac{p(word|label_1)}{p(word|label_2)},&space;\frac{p(word|label_2)}{p(word|label_1)}\right)" target="_blank"><img src="http://latex.codecogs.com/gif.latex?pdtn(label_1,&space;label_2)&space;=&space;arg&space;max\left(&space;\frac{p(word|label_1)}{p(word|label_2)},&space;\frac{p(word|label_2)}{p(word|label_1)}\right)" title="pdtn(label_1, label_2) = arg max\left( \frac{p(word|label_1)}{p(word|label_2)}, \frac{p(word|label_2)}{p(word|label_1)}\right)" /></a>

    \*Note that this measure is symmetric. In other words, how much a feature can distinguish label 1 from label 2 is the same as how much it can distinguish label 2 from label 1.
        
    2. When we have more than 2 labels, we can take the average of the predictivenesses of all label combinations.
        
        <a href="http://www.codecogs.com/eqnedit.php?latex=pdtn(label_1,&space;label_2,&space;label_3)&space;=&space;\frac{pdtn(label_1,&space;label_2)&space;&plus;&space;pdtn(label_1,&space;label_3)&space;&plus;&space;pdtn(label_2,&space;label_3)}{3}" target="_blank"><img src="http://latex.codecogs.com/gif.latex?pdtn(label_1,&space;label_2,&space;label_3)&space;=&space;\frac{pdtn(label_1,&space;label_2)&space;&plus;&space;pdtn(label_1,&space;label_3)&space;&plus;&space;pdtn(label_2,&space;label_3)}{3}" title="pdtn(label_1, label_2, label_3) = \frac{pdtn(label_1, label_2) + pdtn(label_1, label_3) + pdtn(label_2, label_3)}{3}" /></a>

    3. At last this predictiveness of feature word should be weighted by the count of this word. The more frequent this word appears, the more reliable this predictiveness is.

    <a href="http://www.codecogs.com/eqnedit.php?latex=pdtn&space;=&space;pdtn&space;\times&space;count" target="_blank"><img src="http://latex.codecogs.com/gif.latex?pdtn&space;=&space;pdtn&space;\times&space;count" title="pdtn = pdtn \times count" /></a>

    ```python
    >>> Input:
        def elementWiseAdd(list_1, list_2):
            """ Add up 2 lists element-wisely"""
            return [a + b for a, b in zip(list_1, list_2)]

        def calcPDTN(cps):
            """ takes in the conditional probablities of one feature 
            and calculate the predictiveness of this feature.
            """
            cp0, cp1, cp2 = tuple(cps)
            f    = lambda a, b: round(max(a/b, b/a), 5)
            pdtn = (f(cp0, cp1) + f(cp0, cp2) + f(cp1, cp2))/3

            return (cp0, cp1, cp2, pdtn)

        def weightByCount(rdd_a, rdd_b):
            """ Weight the predictiveness of features by their counts."""
            cnts    = rdd_b.collect()
            rdd_new = rdd_a.map(lambda x: (x[0], (x[1][3]*cnts[x[0]], cnts[x[0]])))
            
            return rdd_new
                
        def zipWithWords(rdd_a, rdd_b):
            """ Replace the feature index with word.
            """
            words_ = rdd_b.collect()
            return rdd_a.map(lambda x: (words_[x[0]], x[1]))

        # For each RDD in stream:
        # - reduce the RDD by key(tag) so that each RDD has only 3 rows,
        #   each row has 3 elements: the tag, counts of appearances 
        #   of each feature word in the tweets and the count of tweets 
        #   under this tag.
        # get 3 rows corresponding to 3 tags: 
        #   (tag, ([featCnt_0, featCnt_1, ..., featCnt_4999], tweetCnt))
        # - divide the count of each feature word by the count of tweets
        #   to get the conditional probability. 
        # get 3 rows: (tag, [cp_0, cp_1, ..., cp_4999])
        # - for each row, combine each conditional probability with feature index
        # get 3 rows: 
        #       ((0, cp0_0), (1, cp0_1), ..., (4999, cp0_4999))
        #       ((0, cp1_0), (1, cp1_1), ..., (4999, cp1_4999))
        #       ((0, cp2_0), (1, cp2_1), ..., (4999, cp2_4999))
        # - flatmap these 3 rows
        # get 15000 rows: (m, cp#_m)
        # - reduce by key(index) to combine cps for different tags
        # get 5000 rows: (index, (cp0_m, cp1_m, cp2_m))
        # - for each row, calculate predictiveness using conditional prob
        # get 5000 rows: (index, (cp0_m, cp1_m, cp2_m, pdtn_m))
        # - weight the pdtn by the count of the words
        # get 5000 rows: (index_m, (weightedPDTN_m, count_m))
        # - replace the word index by the actual word
        # get 5000 rows: (word_m, (weightedPDTN_m, count_m))
        featureStats = dataset_train\
            .reduceByKey(lambda a, b: (elementWiseAdd(a[0], b[0]), a[1]+b[1]))\
            .mapValues(lambda x: [(count+1)/x[1] for count in x[0]])\
            .map(lambda x: [(i, cp) for i, cp in enumerate(x[1])])\
            .flatMap(lambda x: x)\
            .mapValues(lambda x: [x])\
            .reduceByKey(lambda a, b: a + b)\
            .map(lambda x: (x[0], calcPDTN(x[1])))\
            .transformWith(weightByCount, counts)\
            .transformWith(zipWithWords, words)

    >>> Output:
        "
        # most predictive word : (cp0, cp1, cp2, pdtn) 
        allstar     : (0.14835164835164835, 0.0078125, 0.05555555555555555, 249.3439)  
        alabama     : (0.005494505494505495, 0.140625, 0.05555555555555555, 216.67129)  
        fitzpatrick : (0.005494505494505495, 0.1328125, 0.05555555555555555, 195.5925333333333)  
        voting      : (0.12637362637362637, 0.0078125, 0.05555555555555555, 187.45217333333335)  
        minkah      : (0.005494505494505495, 0.125, 0.05555555555555555, 175.55554999999998)  
        draft       : (0.016483516483516484, 0.171875, 0.1111111111111111, 149.7176)  
        ...  
        "
    ```

3. Update feature predictiveness dictionary
    We are keeping a dictionary of feature words and their corresponding predictiveness.
    ```python
        def updateWordStats(newValue, oldValue):
            """ Update the word stats with new data.
            
            Inputs:
            -------
            newValue: (weightedPDTN_m, count_m) tuples in this round
            oldValue: (weightedPDTN_m, count_m) tuples up to last round.
            
            Output:
            -------
            (PDTN_new, count_m) tuples upto this round.

            """
            oldValue = oldValue or (0, 0)
            count_new = oldValue[1] + newValue[1]
            PDTN_new = (oldValue[0] * oldValue[1] + newValue[0] * newValue[1])/count_new
            
            return (PDTN_new, count_new)
           
        # For each RDD in stream:
        # - merge with the old state and generate new state
        # get n rows: (word, (weightedPDTN_m, count_m))
        wordStats = featureStats\
            .updateStateByKey(updateWordStats)\
            .transform(lambda rdd: rdd.sortBy(lambda x: -x[1][0]))


    ```

### IV. Validate the learned features on testing tweets
### IV. 验证所学重要特征的有效性
To validate whether this feature predictiveness makes sense, we will visualize testing tweets based on the learned most predictive features.

1. Under each label, 60 tweets are selected from the testing tweets. These 180 tweets are encoded as structured dataset using 300 most predictive features selected out of 5000.

    ```python
    >>> Input:
        def fetchFeatsTweets(rdd_a, rdd_b):
            """ Given predictiveness of each feature word, fetch 300 most
            predictive features and 180 most predictable tweets under 3 tags
            from encoded dataset.
            """
            # For each RDD:
            # - take the word and pdtn of features
            # get 5000 rows: (word, pdtn_i)
            # - sort by pdtn
            # get 5000 rows: (word, pdtn_i)
            # - take the first 300 rows
            # get 300 rows: (word, pdtn_i)
            predFeats = rdd_b\
                .map(lambda x: (x[0], x[1][3]))\
                .sortBy(lambda x: -x[1])\
                .take(num=300)

            words = predFeats.map(lambda x: x[0]).collect()
            pdtns = predFeats.map(lambda x: x[1]).collect()
                
            sumPDTN = lambda a, b: sum([i*k for i, k in zip(a, b)])
            
            # for each row in rdd:
            # has n rows: (tag, ([feat_0, ..., feat_4999], 1))
            # - keeps only high predictive features
            # get n rows: (tag, [feat_0, ..., feat_299])
            # - calculate the sum pdtn
            # get n rows: (tag, [feat_0, ..., feat_299], sumPDTN)
            # - take the first 60 rows:
            # get 60 rows: (tag, [feat_0, ..., feat_299], sumPDTN)
            rdd_new = rdd_a\
                .map(lambda x: (x[0], [x[1][0][i] for i in indices]))\
                .map(lambda x: (x[0], x[1], sumPDTN(x[1], pdtns)))\
                .take(num=60)
            
            return rdd_new

        # for each tag, filter dataset DStream with corresponding tag
        # fetch high predictive features and predictable tweets.
        ds_0 = cleanTweets_test.filter(lambda x: x[0] == 0)\
            .transformWith(fetchFeatsTweets, wordStats)
        ds_1 = cleanTweets_test.filter(lambda x: x[0] == 1)\
            .transformWith(fetchFeatsTweets, wordStats)
        ds_2 = cleanTweets_test.filter(lambda x: x[0] == 2)\
            .transformWith(fetchFeatsTweets, wordStats)
              
        # concatenate 3 DStreams together
        # get 300 rows: (tag, [feat_0, ..., feat_99], sumPDTN)
        selectedTweets = ds_0.union(ds_1).union(ds_2)

    >>> Output:
        "
        0, [1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, ...],151.33585333333332
        0, [1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, ...],151.33585333333332
        0, [1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, ...],143.13223666666667
        0, [1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, ...],143.13223666666667
        0, [1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, ...],143.13223666666667
        "
    ```

2. Since the dataset we have are sparse and have binary values, here we use non-linear method t-SNE to learn the 2-d manifold the dataset lies on to obtain x values and y values for our each tweet. The tweets are then visualized as scatter plot. In the scatter, each circle represents a tweet. The color is identified by the tag-NBA tweets will be red, NFL tweets will be blue and MLB ones will be green. The size and alpha of circle is identified by the sum of predictivenesses of each tweet. And the x, y values are 2 dimensions coming out of t-SNE. If the circles of same color are easily distinguishable from the other colors, then the features are effective for classifying this tag.

    ```python
    >>> Input:
        def collectPDS(rdd):
            """ collect the tag, feature values and predictiveness sum 
            and fit-transform the features with TSNE.
            """
            global tsne_0, tsne_1, color, label, alpha, t_1
            
            # transform tags indices to colors, and tags
            # collect data to master machine
            pData = rdd.map(lambda x: (cols[x[0]], tags[x[0]], x[2], x[1]))
            pData = pData.collect()
            
            # reduce the dimensionality to 2 using t-SNE
            # scale the learned features to range [0, 1]
            array  = np.array([x[3] for x in pData])
            if len(array.shape) == 1: 
                array = array.reshape(1, -1)
            embed  = TSNE(n_components=2).fit_transform(array)
            tsne_0 = minMaxScale(embed[:, 0])
            tsne_1 = minMaxScale(embed[:, 1])
            
            color = [x[0] for x in pData]
            label = [x[1] for x in pData]
            alpha = [x[2] for x in pData]
        
        selectedTweets.foreachRDD(collectPDS)

    >>> Output:
        "
        # plotting data source:
        Total number of tweets:138
        Number of NBA tweets; NFL tweets; MLB tweets : [60, 60, 18]
        x     : [ 0.17929186  0.18399966  0.63295108  0.17661807...]
        y     : [ 0.62392987  0.66881742  0.69876889  0.36454208...]
        color : ['red', 'red', 'red', 'red'...]
        tags  : ['nba', 'nba', 'nba', 'nba'...]
        size  : [0.0042378419396584864, 0.0042378419396584864, 0.0042378419396584864, 0.0042378419396584864...]
        alpha : [ 0.42378419  0.42378419  0.42378419  0.42378419...]
        "
    ```

![](imgs/tweet_feature_learning.gif)


    
## To run the notebook:
## 使用此 Jupyter Notebook 的方法
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
    docker run -it -v ~/Projects/streaming-tweet-feature-learning:/home/jovyan -p 8888:8888 xianlai/spark_project

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


## Dependencies
## 所使用的Python库
- **Spark**: URL:http://spark.apache.org/
- **Tweepy** : URL:http://www.tweepy.org/
- **Bokeh**: Bokeh Development Team (2014). Bokeh: Python library for interactive visualization. URL:http://www.bokeh.pydata.org.


## License
## 使用许可证
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


![](https://i.imgur.com/LH6GvZm.png)

## Overview 
The WormRuler software is an open-source python based video analysis tool to analyze body length of _Caenorhabditis elegans_, developed by Marius Seidenthal and Dennis Vettkötter as part of their PhD thesis in the Gottschalk Lab, Goethe University Frankfurt, Germany.

## Getting started

### Installation

Download the [latest release](https://github.com/dvettkoe/wormruler/releases/tag/v1.1.0), unzip the folder and start the _"wormruler_v*.exe"_.

### WormRuler guide

WormRuler offers an user-friendly graphical user interface (GUI) that offers a step-by-step guidance for the analysis of multiple single worm videos.

![](https://i.imgur.com/VjMOw95.gif)

WormRuler allows the user to start each step separately or start all at once.

#### 1. Select videos to be analyzed
Select the main directory in which your videos are stored.

(WormRuler supports only the following file types: **.avi/.AVI** or **.mov/.MOV**)

**Careful**: WormRuler requires a specific structure of folders:

>	    main folder -> subfolder for condition 1 -> videos of condition 1
>	
>                   -> subfolder for condition 2 -> videos of condition 2
>				        	
>                   ...
>					        
>                   -> subfolder for condition n -> videos of condition n 
>					        
WormRuler is currently only able to analyze a single worm per video.

Users can now start each step one by one or start all step at once by clicking "Start all".

#### 2. Background correction
Enter Gamma value depending on the brightness of the video. The gamma value should be between 0.7 to 1.3.

We recommend to start background correction for one video and adjust the gamma value accordingly. The Preview button may be used to test whether the gamma value is appropriate. Background corrected videos should look like above.

#### 3. Skeletonize
Adjust the framerate to match the framerate of your videos.

Check the box to override already analyzed videos. This option can be useful, if the gamma value was not adjusted correctly and analysis has to be repeated.

After starting, WormRuler will ask to select a ROI. This can be used to avoid rims and unwanted artifacts in your videos.

<img src="https://i.imgur.com/ytdtDWe.png" width="50%" height="50%">


#### 4. Normalize Data
When using a stimulus in your experiment (e.g. light pulse) insert the time (in seconds) for the start of the pulse.

Measured skeleton length (in pixel) are normalized to this time point.

_If no stimulus was given in the experiment insert any time point for normalization (e.g. 1 s)_

#### 5. Analyze Data
Normalized data will be summarized for each analyzed condition and exported into an XLSX format for further analysis.

Normalized values for each analyzed worm as well as mean, standard error of the mean and n numbers will be given.

When more than 50 % of the datapoints of an animal are omitted, it will be ignored in the statistical analysis and listed separately.

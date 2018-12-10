# Intention prediction 

An introduction to intention prediction scenario and data set.


## Experiment scenario

<p align="center">
<img width="450"  src="https://github.com/fantasylsc/Intention_Prediction/blob/master/images/Experiment.PNG" >
</p>

The experiment is about a human participant pitching a ball toward a robot (represented by a target area in the figure). The target area is divided into 9 grids which represent the 9 targets that the ball can hit. We expect the robot to be able to predict the intention of the participant (i.e., which of the nine targets the participant is pitching the ball to). 




## Data set





## Others
1. data_acquire: capture 3 sec video by Kinect V2 under Matlab and save the data.

2. dataset_utils:
- `travaltes_slicing.py` slices dataset to train/validation/test by proportion of 6/2/2.
- `create_pitch_tf_record.py` create tfrecord shards.

3. `pitch2d_main.py` training and evaluation.

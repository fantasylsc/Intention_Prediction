"""Converts Pitch2d data to TFRecords file format with Example protos.

The raw Pitch2d data set is expected to reside in PNG files located in the
following directory structure.

  data_dir/intent##/ID/datetime_trial##/trial_datetime_frame_####.png
  e.g.: /data_dir/intent02/ZL/201801302254_trial08/trial_201801302254_frame0045.png
  ...

where 'intent##' is the unique label associated with
these images.

The training data set consists of 9 sub-directories (i.e. labels)
each containing 1080 PNG images for a total of 9720 PNG images.

The evaluation data set consists of 9 sub-directories (i.e. labels)
each containing 380 PNG images for a total of 3420 PNG images.

The testing data set consists of 9 sub-directories (i.e. labels)
each containing 380 PNG images for a total of 3420 PNG images.

This TensorFlow script converts the training, evaluation and testing data into
a sharded data set consisting of 16, 8 and 8 TFRecord files, respectively.

  train_directory/train-00-of-16
  train_directory/train-01-of-16
  ...
  train_directory/train-16-of-16

and

  validation_directory/validation-00-of-08
  validation_directory/validation-01-of-08
  ...
  validation_directory/validation-08-of-08

and

  test_directory/test-00-of-08
  test_directory/test-01-of-08
  ...
  test_directory/test-08-of-08


Each training TFRecord file contains ~608 records. Each validation TFRecord 
file contains ~428 records. Each testing TFRecord file contains ~428 records. 
Each record within the TFRecord file is a serialized Example proto. 
The Example proto contains the following fields:

  image/encoded: string containing PNG encoded image in RGB colorspace
  image/height: integer, image height in pixels
  image/width: integer, image width in pixels
  image/colorspace: string, specifying the colorspace, always 'RGB'
  image/channels: integer, specifying the number of channels, always 3
  image/format: string, specifying the format, always 'JPEG' or 'PNG'

  image/filename: string containing the basename of the image file
            e.g. 'trial_201801302254_frame0045.png'
  image/class/label: integer specifying the index in a classification layer.
    The label ranges from [1, 9] where 0 is not used.
  image/class/pid: string specifying the unique ID of the pitcher,
    e.g. 'ZL'

Running this script using 8 threads may take around ~? hours 
on an Alienware Aurora R6.

Running this script using 16 threads may take around ~? hours 
on an Threadripper 1900X + ASRock X399 Taichi.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from datetime import datetime
import os
import glob
import random
import sys
import threading

import numpy as np
import scipy.io as spio
import six
import tensorflow as tf


DATA_DIR = '/media/linzhank/DATA/Works/Intention_Prediction/Dataset/Ball pitch/pit2d9blk'

tf.app.flags.DEFINE_string('train_directory', '/tmp/',
                           'Training data directory')
tf.app.flags.DEFINE_string('validation_directory', '/tmp/',
                           'Validation data directory')
tf.app.flags.DEFINE_string('test_directory', '/tmp/',
                           'Test data directory')
tf.app.flags.DEFINE_string('output_directory', '/tmp/',
                           'Output data directory')

tf.app.flags.DEFINE_integer('train_shards', 1024,
                            'Number of shards in training TFRecord files.')
tf.app.flags.DEFINE_integer('validation_shards', 128,
                            'Number of shards in validation TFRecord files.')

tf.app.flags.DEFINE_integer('num_threads', 8,
                            'Number of threads to preprocess the images.')

FLAGS = tf.app.flags.FLAGS


def _int64_feature(value):
  """Wrapper for inserting int64 features into Example proto."""
  if not isinstance(value, list):
    value = [value]
  return tf.train.Feature(int64_list=tf.train.Int64List(value=value))


def _float_feature(value):
  """Wrapper for inserting float features into Example proto."""
  if not isinstance(value, list):
    value = [value]
  return tf.train.Feature(float_list=tf.train.FloatList(value=value))


def _bytes_feature(value):
  """Wrapper for inserting bytes features into Example proto."""
  if isinstance(value, six.string_types):           
    value = six.binary_type(value, encoding='utf-8') 
  return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def _convert_to_example(filename, image_buffer, label, height, width):
  """Build an Example proto for an example.

  Args:
    filename: string, path to an image file, e.g., '/path/to/example.JPG'
    image_buffer: string, JPEG encoding of RGB image
    label: integer, identifier for the ground truth for the network
    synset: string, unique WordNet ID specifying the label, e.g., 'n02323233'
    human: string, human-readable label, e.g., 'red fox, Vulpes vulpes'
    bbox: list of bounding boxes; each box is a list of integers
      specifying [xmin, ymin, xmax, ymax]. All boxes are assumed to belong to
      the same label as the image label.
    height: integer, image height in pixels
    width: integer, image width in pixels
  Returns:
    Example proto
  """
  colorspace = 'RGB'
  channels = 3
  image_format = 'JPEG'

  example = tf.train.Example(features=tf.train.Features(feature={
      'image/height': _int64_feature(height),
      'image/width': _int64_feature(width),
      'image/colorspace': _bytes_feature(colorspace),
      'image/channels': _int64_feature(channels),
      'image/class/label': _int64_feature(label),
      'image/format': _bytes_feature(image_format),
      'image/filename': _bytes_feature(os.path.basename(filename)),
      'image/encoded': _bytes_feature(image_buffer)}))
  return example


class ImageCoder(object):
  """Helper class that provides TensorFlow image coding utilities."""

  def __init__(self):
    # Create a single Session to run all image coding calls.
    self._sess = tf.Session()

    # Initializes function that decodes RGB JPEG data.
    self._decode_image_data = tf.placeholder(dtype=tf.string)
    self._decode_image = tf.image.decode_image(self._decode_image_data, channels=3)

  def decode_image(self, image_data):
    image = self._sess.run(self._decode_image,
                           feed_dict={self._decode_image_data: image_data})
    assert len(image.shape) == 3
    assert image.shape[2] == 3
    return image


def _process_image(filename, coder):
  """Process a single image file.

  Args:
    filename: string, path to an image file e.g., '/path/to/example.JPG'.
    coder: instance of ImageCoder to provide TensorFlow image coding utils.
  Returns:
    image_buffer: string, JPEG encoding of RGB image.
    height: integer, image height in pixels.
    width: integer, image width in pixels.
  """
  # Read the image file.
  with tf.gfile.FastGFile(filename, 'rb') as f:
    image_data = f.read()

  # Decode the RGB JPEG.
  image = coder.decode_image(image_data)

  # Check that image converted to RGB
  assert len(image.shape) == 3
  height = image.shape[0]
  width = image.shape[1]
  assert image.shape[2] == 3

  return image_data, height, width


def _process_image_files_shards(coder, ranges, filenames, labels, num_shards):
  """Processes and saves list of images as TFRecord in 1 shard.

  Args:
    coder: instance of ImageCoder to provide TensorFlow image coding utils.
    ranges: list of pairs of integers specifying ranges of each shard.
    filenames: list of strings; each string is a path to an image file
    labels: list of integer; each integer identifies the ground truth
    num_shards: integer number of shards for this data set.
  """
  # 
  num_files_in_shard = ranges[1] - ranges[thread_index][0]

  for s in range(num_shards):
    # Generate a sharded version of the file name, e.g. 'train-00002-of-00010'
    output_filename = "{}-{:05d}-of-{:05d}".format(name, shard, num_shards)
    output_file = os.path.join(FLAGS.output_directory, output_filename)
    writer = tf.python_io.TFRecordWriter(output_file)

    shard_counter = 0
    indices_in_shard = np.arange(ranges[s][0], ranges[s][1], dtype=int)
    labels_in_shard = labels[ranges[s][0]:ranges[s][1]]
    counter = 0
    for i in indices_in_shard:
      filename = filenames[i]
      label = labels[i]

      image_buffer, height, width = _process_image(filename, coder)

      example = _convert_to_example(filename, image_buffer, label, height, width)
      writer.write(example.SerializeToString())
      counter += 1

      print("{} [ shard-{:d}]: Processed {:d} of {:d} images in shard.".format
              (datetime.now(), s, counter, len(indices_in_shard)))
      sys.stdout.flush()

    writer.close()
    shard_counter += 1
    print("==== {} [shard-{:d}] wrote to {}".format
          (datetime.now(), shard_counter, output_file))
    sys.stdout.flush()


def _process_image_files(filenames, labels, num_shards):
  """Process and save list of images as TFRecord of Example protos.

  Args:
    filenames: list of strings; each string is a path to an image file
    labels: list of integer; each integer identifies the ground truth
    num_shards: integer number of shards for this data set.
  """
  assert len(filenames) == len(labels)

  # Break all images into batches with a [ranges[i][0], ranges[i][1]].
  spacing = np.linspace(0, len(filenames), num_shards + 1).astype(np.int)
  ranges = []
  for i in range(len(spacing) - 1):
    ranges.append([spacing[i], spacing[i + 1]])

  # Create a generic TensorFlow-based utility for converting all image codings.
  coder = ImageCoder()

  # create tfrecord shard by shard
  _process_image_files_batch(coder, ranges, filenames, labels, num_shards)

  print('{} Finished writing all {} images in data set.'.format(datetime.now(), len(filenames)))
  sys.stdout.flush()

def find_pitch_init(joint_path, intent, pitcher, trial):
  """Find the initiating moment of each pitching trial.
  
  Args: 
    joint_path: string, path to the root dirctory of pitch data
    intent: string, pitching intent with numbers e.g. "intent02"
    pitcher: string, pitcher's name e.g. "ZL"
    trial: string, trial id with timestamp e.g. trial_201801302254

  Returns:
    dist: list of float, each float number indicate the euclidean distance between 
      joint positions of current frame and joint positions of first frame. 
    init_frame_id: integer, this number indicate the frame index of the pitching initiation.
  """
  matfile_path = os.path.join(joint_path, intent, pitcher, trial, '*.mat')
  matfile_name = glob.glob(matfile_path)[0]
  joint_position = spio.loadmat(matfile_name)['joint_positions_3d']
  window_size = 20
  dist = []
  for i in range(joint_position.shape[2]):
    d = np.linalg.norm(joint_position[:,:,i] - joint_position[:,:,0])
    dist.append(d)
  inc_inarow = 0
  di = 0 # index of distance
  while di < len(dist)-45 and inc_inarow <= window_size:
    if dist[di+1] > dist[di]:
      inc_inarow += 1
    else:
      inc_inarow = 0
    di += 1
  initframe = di - window_size
  return dist, initframe 

def _find_image_files(data_dir):
  """Build a list of all images files and labels in the data set.

  Args:
    data_dir: string, path to the root directory of images.

      Assumes that the ImageNet data set resides in PNG files located in
      the following directory structure.
        data_dir/intent##/ID/datetime_trial##/trial_datetime_frame_####.png

      We start the integer labels at 1 is to reserve label 0 as an
      unused background class.

  Returns:
    trainpaths: list of strings; each string is a path to an image file.
    validatepaths: list of strings; each string is a path to an image file.
    testpaths: list of strings; each string is a path to an image file.
    trainlabels: list of integer; each integer identifies the ground truth.
    validatelabels: list of integer; each integer identifies the ground truth.
    testlabels: list of integer; each integer identifies the ground truth.
  """
  color_path = os.path.join(data_dir, 'color')
  joint_path = os.path.join(data_dir, 'joint')
  print('Determining list of input files and labels from %s.' % data_dir)
  # Prepare training, validation and test data 
  trainpaths = []
  validatepaths = []
  testpaths = []

  trainlabels = []
  validatelabels = []
  testlabels = []

  intents = []
  labels = []
  filenames = []

  # Leave label index 0 empty as a background class.
  label_index = 1

  # Construct the list of PNG files and labels.
  intent_paths = sorted(glob.glob(color_path+'/*'))
  for ipath in intent_paths:
    intent = ipath.split('/')[-1]
    intents.append(intent)
    labels.append(label_index)

    pitcher_paths = sorted(glob.glob(ipath+'/*'))
    for ppath in pitcher_paths:
      pitcher = ppath.split('/')[-1]
      trial_paths = sorted(glob.glob(ppath+'/*'))
      np.random.shuffle(trial_paths) # shuffle all 10 trials, before travaltes arrangement
      #separate images to train, val, test (travaltes), 6/2/2
      train_trial_paths = trial_paths[:int(0.6*len(trial_paths))]
      val_trial_paths = trial_paths[int(0.6*len(trial_paths)):int(0.8*len(trial_paths))]
      test_trial_paths = trial_paths[int(0.8*len(trial_paths)):]
      for trnpath in train_trial_paths:
        trial = trnpath.split('/')[-1]
        _, init_frmid = find_pitch_init(joint_path, intent, pitcher, trial)
        train_img_paths = sorted(glob.glob(trnpath+'/*.png'))[init_frmid:init_frmid+45]
        trainpaths += train_img_paths
        trainlabels += [label_index] * len(train_img_paths)

      for valpath in val_trial_paths:
        trial = trnpath.split('/')[-1]
        _, init_frmid = find_pitch_init(joint_path, intent, pitcher, trial)
        val_img_paths = sorted(glob.glob(valpath+'/*.png')[init_frmid:init_frmid+45])
        validatepaths += val_img_paths
        validatelabels += [label_index] * len(val_img_paths)

      for tespath in test_trial_paths:
        trial = trnpath.split('/')[-1]
        _, init_frmid = find_pitch_init(joint_path, intent, pitcher, trial)
        test_img_paths = sorted(glob.glob(tespath+'/*.png')[init_frmid:init_frmid+45])
        testpaths += test_img_paths
        testlabels += [label_index] * len(test_img_paths)

    # Construct the list of PNG files and labels
    print('Finished finding files in {}.'.format(intent))
    label_index += 1 # label index increase when investigating new intent

  print('Found {num_trn} images for training; \nFound {num_val} images for validating; \nFound {num_tes} images for testing.'.format(num_trn=len(trainpaths),
                                                                                                                                     num_val=len(validatepaths),
                                                                                                                                     num_tes=len(testpaths)))

  return trainpaths, validatepaths, testpaths, trainlabels, validatelabels, testlabels


def _process_dataset(name, directory, num_shards):
  """Process a complete data set and save it as a TFRecord.

  Args:
    name: string, unique identifier specifying the data set.
    directory: string, root path to the data set.
    num_shards: integer number of shards for this data set.
  """
  filenames, labels = _find_image_files(directory, FLAGS.labels_file)
  _process_image_files(name, filenames, labels, num_shards)

def main(unused_argv):
  assert not FLAGS.train_shards % FLAGS.num_threads, (
      'Please make the FLAGS.num_threads commensurate with FLAGS.train_shards')
  assert not FLAGS.validation_shards % FLAGS.num_threads, (
      'Please make the FLAGS.num_threads commensurate with '
      'FLAGS.validation_shards')
  assert not FLAGS.test_shards % FLAGS.num_threads, (
      'Please make the FLAGS.num_threads commensurate with '
      'FLAGS.test_shards')
  print('Saving results to %s' % FLAGS.output_directory)

  # Run it!
  _process_dataset('validation', FLAGS.validation_directory,
                   FLAGS.validation_shards, synset_to_human, image_to_bboxes)
  _process_dataset('train', FLAGS.train_directory, FLAGS.train_shards,
                   synset_to_human, image_to_bboxes)
  _process_dataset('test', FLAGS.test_directory, FLAGS.test_shards, pitcher_id)


if __name__ == '__main__':
  tf.app.run()

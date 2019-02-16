# coding=utf-8
# Copyright 2018 The Conversation-AI.github.io Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for tfrecord_input."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf

from tf_trainer.common import base_model
from tf_trainer.common import tfrecord_input
from tf_trainer.common import types

FLAGS = tf.app.flags.FLAGS


class TFRecordInputTest(tf.test.TestCase):

  def setUp(self):
    FLAGS.text_feature = 'comment'
    ex = tf.train.Example(
        features=tf.train.Features(
            feature={
                'label':
                    tf.train.Feature(
                        float_list=tf.train.FloatList(value=[0.8])),
                'ignored-label':
                    tf.train.Feature(
                        float_list=tf.train.FloatList(value=[0.125])),
                'int_label':
                    tf.train.Feature(int64_list=tf.train.Int64List(value=[0])),
                'comment':
                    tf.train.Feature(
                        bytes_list=tf.train.BytesList(
                            value=['Hi there Bob'.encode('utf-8')]))
            }))
    self.ex_tensor = tf.convert_to_tensor(
        ex.SerializeToString(), dtype=tf.string)

  def test_TFRecordInput_unrounded(self):
    FLAGS.round_labels = False
    FLAGS.labels = 'label'
    dataset_input = tfrecord_input.TFRecordInput()

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(features[base_model.TEXT_FEATURE_KEY].eval(),
                       b'Hi there Bob')
      np.testing.assert_almost_equal(labels['label'].eval(), 0.8)
      np.testing.assert_almost_equal(features['label_weight'].eval(), 1.0)
      self.assertCountEqual(list(labels), ['label'])
      self.assertCountEqual(list(features), ['text', 'label_weight', base_model.EXAMPLE_KEY])

  def test_TFRecordInput_default_values(self):
    FLAGS.labels = 'label,fake_label,int_label'
    FLAGS.label_dtypes = 'float,float,int'
    FLAGS.round_labels = False
    dataset_input = tfrecord_input.TFRecordInput()

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(features[base_model.TEXT_FEATURE_KEY].eval(),
                       b'Hi there Bob')
      np.testing.assert_almost_equal(labels['label'].eval(), 0.8)
      np.testing.assert_almost_equal(labels['int_label'].eval(), 0.0)
      np.testing.assert_almost_equal(features['label_weight'].eval(), 1.0)
      np.testing.assert_almost_equal(labels['fake_label'].eval(), 0.0)
      np.testing.assert_almost_equal(features['fake_label_weight'].eval(), 0.0)

  def test_TFRecordInput_rounded(self):
    FLAGS.labels = 'label'
    FLAGS.round_labels = True
    dataset_input = tfrecord_input.TFRecordInput()

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(features[base_model.TEXT_FEATURE_KEY].eval(),
                       b'Hi there Bob')
      np.testing.assert_almost_equal(labels['label'].eval(), 1.0)
      np.testing.assert_almost_equal(features['label_weight'].eval(), 1.0)

  def test_TFRecordInput_example_key(self):
    FLAGS.labels = 'label'
    dataset_input = tfrecord_input.TFRecordInput()

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(features[base_model.EXAMPLE_KEY].eval(), -1.0)


class TFRecordInputWithTokenizerTest(tf.test.TestCase):

  def setUp(self):
    FLAGS.text_feature = 'comment'
    ex = tf.train.Example(
        features=tf.train.Features(
            feature={
                'label':
                    tf.train.Feature(
                        float_list=tf.train.FloatList(value=[0.8])),
                'int_label':
                    tf.train.Feature(int64_list=tf.train.Int64List(value=[0])),
                'comment':
                    tf.train.Feature(
                        bytes_list=tf.train.BytesList(
                            value=['Hi there Bob'.encode('utf-8')]))
            }))
    self.ex_tensor = tf.convert_to_tensor(
        ex.SerializeToString(), dtype=tf.string)

    self.word_to_idx = {'Hi': 12, 'there': 13}
    self.unknown_token = 999

  def preprocessor(self, text):
    return tf.py_func(
        lambda t: np.asarray([
            self.word_to_idx.get(x, self.unknown_token)
            for x in t.decode('utf-8').split(' ')
        ]), [text], tf.int64)

  def test_TFRecordInputWithTokenizer_unrounded(self):
    FLAGS.labels = 'label,fake_label,int_label,fake_int_label'
    FLAGS.label_dtypes = 'float,float,int,int'
    FLAGS.round_labels = False
    dataset_input = tfrecord_input.TFRecordInputWithTokenizer(
        train_preprocess_fn=self.preprocessor)

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(
          list(features[base_model.TOKENS_FEATURE_KEY].eval()), [12, 13, 999])
      self.assertAlmostEqual(labels['label'].eval(), 0.8)
      self.assertAlmostEqual(labels['fake_label'].eval(), 0.0)
      self.assertAlmostEqual(labels['int_label'].eval(), 0.0)
      self.assertAlmostEqual(labels['fake_int_label'].eval(), 0.0)
      self.assertAlmostEqual(features['label_weight'].eval(), 1.0)
      self.assertAlmostEqual(features['fake_label_weight'].eval(), 0.0)
      self.assertAlmostEqual(features['int_label_weight'].eval(), 1.0)
      self.assertAlmostEqual(features['fake_int_label_weight'].eval(), 0.0)

  def test_TFRecordInputWithTokenizer_default_values(self):
    FLAGS.labels = 'label,fake_label'
    FLAGS.round_labels = False
    dataset_input = tfrecord_input.TFRecordInputWithTokenizer(
        train_preprocess_fn=self.preprocessor)

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(
          list(features[base_model.TOKENS_FEATURE_KEY].eval()), [12, 13, 999])
      self.assertAlmostEqual(labels['label'].eval(), 0.8)
      self.assertAlmostEqual(labels['fake_label'].eval(), 0.0)
      self.assertAlmostEqual(features['label_weight'].eval(), 1.0)
      self.assertAlmostEqual(features['fake_label_weight'].eval(), 0.0)

  def test_TFRecordInputWithTokenizer_rounded(self):
    FLAGS.labels = 'label'
    FLAGS.round_labels = True
    dataset_input = tfrecord_input.TFRecordInputWithTokenizer(
        train_preprocess_fn=self.preprocessor)

    with self.test_session():
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(
          list(features[base_model.TOKENS_FEATURE_KEY].eval()), [12, 13, 999])
      self.assertEqual(labels['label'].eval(), 1.0)
      self.assertEqual(features['label_weight'].eval(), 1.0)

  def test_TFRecordInputWithTokenizer_example_key(self):
    FLAGS.labels = 'label'
    dataset_input = tfrecord_input.TFRecordInputWithTokenizer(
        train_preprocess_fn=self.preprocessor)

    with self.test_session() as s:
      features, labels = dataset_input._read_tf_example(self.ex_tensor)
      self.assertEqual(features[base_model.EXAMPLE_KEY].eval(), -1.0)


if __name__ == '__main__':
  tf.test.main()

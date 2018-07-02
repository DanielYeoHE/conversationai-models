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

from tf_trainer.common import tfrecord_input
from tf_trainer.common import types

import numpy as np
import tensorflow as tf


class TFRecordInputTest(tf.test.TestCase):

  def test_read_tf_example(self):
    ex = tf.train.Example(
        features=tf.train.Features(
            feature={
                "label":
                    tf.train.Feature(
                        float_list=tf.train.FloatList(value=[0.8])),
                "comment":
                    tf.train.Feature(
                        bytes_list=tf.train.BytesList(
                            value=["Hi there Bob".encode("utf-8")]))
            }))
    ex_tensor = tf.convert_to_tensor(ex.SerializeToString(), dtype=tf.string)

    word_to_idx = {"Hi": 12, "there": 13}
    unknown_token = 999

    def preprocessor(text):
      return tf.py_func(
          lambda t: np.asarray([word_to_idx.get(x, unknown_token) for x in t.decode().split(" ")]),
          [text], tf.int64)

    dataset_input = tfrecord_input.TFRecordInput(
        train_path=None,
        validate_path=None,
        text_feature="comment",
        labels={"label": tf.float32},
        feature_preprocessor=preprocessor,
        round_labels=False)

    with self.test_session():
      features, labels = dataset_input._read_tf_example(ex_tensor)
      self.assertEqual(list(features["comment"].eval()), [12, 13, 999])
      self.assertAlmostEqual(labels["label"].eval(), 0.8)


if __name__ == "__main__":
  tf.test.main()

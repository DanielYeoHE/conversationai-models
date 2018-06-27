"""DatasetInput class based on TFRecord files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import functools
import numpy as np
from tf_trainer.common import dataset_input
from tf_trainer.common import types
from typing import Dict, Tuple, Callable


class TFRecordInput(dataset_input.DatasetInput):
  """TFRecord based DatasetInput.

  Handles parsing of TF Examples.
  """

  def __init__(self,
               train_path: str,
               validate_path: str,
               text_feature: str,
               labels: Dict[str, tf.DType],
               feature_preprocessor: Callable[[types.Tensor], types.Tensor],
               batch_size: int = 64,
               max_seq_length: int = 300) -> None:
    self._train_path = train_path
    self._validate_path = validate_path
    self._text_feature = text_feature
    self._labels = labels
    self._batch_size = batch_size
    self._max_seq_length = max_seq_length
    self._feature_preprocessor = feature_preprocessor

  def train_input_fn(self) -> types.FeatureAndLabelTensors:
    """input_fn for TF Estimators for training set."""
    return self._input_fn_from_file(self._train_path)

  def validate_input_fn(self) -> types.FeatureAndLabelTensors:
    """input_fn for TF Estimators for validation set."""
    return self._input_fn_from_file(self._validate_path)

  def _input_fn_from_file(self, filepath: str) -> tf.data.TFRecordDataset:
    dataset = tf.data.TFRecordDataset(filepath)  # type: tf.data.TFRecordDataset

    parsed_dataset = dataset.map(self._read_tf_example)
    label_shapes = {
        **{label: [] for label in self._labels},
        **{label + "_weight": [] for label in self._labels}
    }
    batched_dataset = parsed_dataset.padded_batch(
        self._batch_size,
        padded_shapes=(
            {
                # TODO: truncate to max_seq_length
                self._text_feature: [None]
            },
            label_shapes))

    itr = batched_dataset.make_one_shot_iterator().get_next()
    return itr

  def _read_tf_example(self, record: tf.Tensor) -> types.FeatureAndLabelTensors:
    """Parses TF Example protobuf into a text feature and labels.

    The input TF Example has a text feature as a singleton list with the full
    comment as the single element.
    """

    keys_to_features = {}
    keys_to_features[self._text_feature] = tf.FixedLenFeature([], tf.string)
    for label, dtype in self._labels.items():
      keys_to_features[label] = tf.VarLenFeature(dtype)
    parsed = tf.parse_single_example(
        record, keys_to_features)  # type: Dict[str, types.Tensor]

    text = parsed[self._text_feature]
    # I think this could be a feature column, but feature columns seem so beta.
    preprocessed_text = self._feature_preprocessor(text)
    features = {self._text_feature: preprocessed_text}
    labels = {
        label: tf.cond(
            tf.size(parsed[label].values) > 0,
            lambda: tf.squeeze(tf.sparse_tensor_to_dense(parsed[label])),
            lambda: 0.0) for label in self._labels
    }
    weights = {
        label + "_weight": tf.to_int32(tf.size(parsed[label].values) > 0)
        for label in self._labels
    }
    labels = {**labels, **weights}

    return features, labels

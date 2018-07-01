"""Keras CNN Model"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tensorflow.python.keras import layers
from tensorflow.python.keras import models
from tensorflow.python.keras import optimizers
from tf_trainer.common import base_keras_model
from tf_trainer.common import types
import tensorflow as tf

from typing import Set, List

FLAGS = tf.app.flags.FLAGS

# Hyperparameters
# TODO: Add validation
tf.app.flags.DEFINE_float('learning_rate', 0.001,
                          'The learning rate to use during training.')
# This would normally just be a multi_integer, but we use string due to
# constraints with ML Engine hyperparameter tuning.
# TODO: add link to relevant public issue/bug/documentation?
tf.app.flags.DEFINE_float('dropout_fraction', 0.1,
                          'The fraction of inputs drop during training.')
# This would normally just be a multi_integer, but we use string due to
# constraints with ML Engine hyperparameter tuning.
# TODO: add link to relevant public issue/bug/documentation?
tf.app.flags.DEFINE_string(
    'filter_sizes', '2,3,4,5,6',
    'Comma delimited string for the sizes of convolution filters.')
tf.app.flags.DEFINE_integer(
    'num_filters', 256,
    'Number of convolutional filters for every convolutional layer.')
# This would normally just be a multi_integer, but we use string due to
# constraints with ML Engine hyperparameter tuning.
# TODO: add link to relevant public issue/bug/documentation?
tf.app.flags.DEFINE_string(
    'dense_units', '1024',
    'Comma delimited string for the number of hidden units in the dense layer.')


class KerasCNNModel(base_keras_model.BaseKerasModel):
  """Keras CNN Model

  Keras implementation of a CNN. Inputs should be
  sequences of word embeddings.
  """

  MAX_SEQUENCE_LENGTH = 300

  def __init__(self, labels: Set[str], optimizer='adam') -> None:
    self._labels = labels

  def hparams(self):
    filter_sizes = [int(units) for units in FLAGS.filter_sizes.split(',')]
    dense_units = [int(units) for units in FLAGS.dense_units.split(',')]
    return tf.contrib.training.HParams(
        learning_rate=FLAGS.learning_rate,
        dropout_fraction=float(FLAGS.dropout_fraction),
        filter_sizes=filter_sizes,
        num_filters=FLAGS.num_filters,
        dense_units=dense_units)

  # Local function you are expected to overwrite.
  def _get_keras_model(self) -> models.Model:
    I = layers.Input(
        shape=(KerasCNNModel.MAX_SEQUENCE_LENGTH, 300),
        dtype='float32',
        name='comment_text')

    # Concurrent convolutional Layers of different sizes
    conv_pools = [] # type: List[types.Tensor]
    for filter_size in self.hparams().filter_sizes:
        x_conv = layers.Conv1D(self.hparams().num_filters, filter_size,
            activation='relu', padding='same')(I)
        x_pool = layers.GlobalAveragePooling1D()(x_conv)
        conv_pools.append(x_pool)
    X = layers.concatenate(conv_pools) # type: types.Tensor

    # Dense Layers after convolutions
    for num_units in self.hparams().dense_units:
      X = layers.Dense(num_units, activation='relu')(X)
      X = layers.Dropout(self.hparams().dropout_fraction)(X)

    # Outputs
    outputs = []
    for label in self._labels:
      outputs.append(layers.Dense(1, activation='sigmoid', name=label)(X))

    model = models.Model(inputs=I, outputs=outputs)
    model.compile(
        optimizer=optimizers.Adam(lr=self.hparams().dropout_fraction),
        loss='binary_crossentropy',
        metrics=['binary_accuracy', super().roc_auc])

    tf.logging.info(model.summary())
    return model

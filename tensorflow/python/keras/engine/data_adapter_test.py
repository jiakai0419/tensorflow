# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
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
# ==============================================================================
"""DataAdapter tests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

from tensorflow.python import keras
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.framework import constant_op
from tensorflow.python.framework import test_util
from tensorflow.python.keras.engine import data_adapter
from tensorflow.python.keras.utils import data_utils
from tensorflow.python.ops import array_ops
from tensorflow.python.platform import test


@test_util.run_all_in_graph_and_eager_modes
class DataAdapterTestBase(test.TestCase):

  def setUp(self):
    super(DataAdapterTestBase, self).setUp()
    self.batch_size = 5
    self.numpy_input = np.zeros((50, 10))
    self.numpy_target = np.ones(50)
    self.tensor_input = constant_op.constant(2.0, shape=(50, 10))
    self.tensor_target = array_ops.ones((50,))
    self.dataset_input = dataset_ops.DatasetV2.from_tensor_slices(
        (self.numpy_input, self.numpy_target)).shuffle(50).batch(
            self.batch_size)

    def generator():
      yield (np.zeros((self.batch_size, 10)), np.ones(self.batch_size))
    self.generator_input = generator()
    self.sequence_input = TestSequence(batch_size=self.batch_size,
                                       feature_shape=10)
    self.model = keras.models.Sequential(
        [keras.layers.Dense(8, input_shape=(10,), activation='softmax')])


class TestSequence(data_utils.Sequence):

  def __init__(self, batch_size, feature_shape):
    self.batch_size = batch_size
    self.feature_shape = feature_shape

  def __getitem__(self, item):
    return (np.zeros((self.batch_size, self.feature_shape)),
            np.ones((self.batch_size,)))

  def __len__(self):
    return 10


class TensorLikeDataAdapterTest(DataAdapterTestBase):

  def setUp(self):
    super(TensorLikeDataAdapterTest, self).setUp()
    self.adapter_cls = data_adapter.TensorLikeDataAdapter

  def test_can_handle_numpy(self):
    self.assertTrue(self.adapter_cls.can_handle(self.numpy_input))
    self.assertTrue(
        self.adapter_cls.can_handle(self.numpy_input, self.numpy_target))

    self.assertFalse(self.adapter_cls.can_handle(self.dataset_input))
    self.assertFalse(self.adapter_cls.can_handle(self.generator_input))
    self.assertFalse(self.adapter_cls.can_handle(self.sequence_input))

  def test_iterator_expect_batch_size_numpy(self):
    with self.assertRaisesRegexp(ValueError, r'`batch_size` is required'):
      self.adapter_cls(self.numpy_input, self.numpy_target)

  def test_size_numpy(self):
    adapter = self.adapter_cls(
        self.numpy_input, self.numpy_target, batch_size=5)
    self.assertEqual(adapter.get_size(), 10)
    self.assertFalse(adapter.has_partial_batch())

  def test_batch_size_numpy(self):
    adapter = self.adapter_cls(
        self.numpy_input, self.numpy_target, batch_size=5)
    self.assertEqual(adapter.batch_size(), 5)

  def test_partial_batch_numpy(self):
    adapter = self.adapter_cls(
        self.numpy_input, self.numpy_target, batch_size=4)
    self.assertEqual(adapter.get_size(), 13)   # 50/4
    self.assertTrue(adapter.has_partial_batch())

  def test_training_numpy(self):
    dataset = self.adapter_cls(
        self.numpy_input, self.numpy_target, batch_size=5).get_dataset()
    self.model.compile(loss='sparse_categorical_crossentropy', optimizer='sgd')
    self.model.fit(dataset)

  def test_can_handle(self):
    self.assertTrue(self.adapter_cls.can_handle(self.tensor_input))
    self.assertTrue(
        self.adapter_cls.can_handle(self.tensor_input, self.tensor_target))

    self.assertFalse(self.adapter_cls.can_handle(self.dataset_input))
    self.assertFalse(self.adapter_cls.can_handle(self.generator_input))
    self.assertFalse(self.adapter_cls.can_handle(self.sequence_input))

  def test_training(self):
    dataset = self.adapter_cls(
        self.tensor_input, self.tensor_target, batch_size=5).get_dataset()
    self.model.compile(loss='sparse_categorical_crossentropy', optimizer='sgd')
    self.model.fit(dataset)

  def test_size(self):
    adapter = self.adapter_cls(
        self.tensor_input, self.tensor_target, batch_size=5)
    self.assertEqual(adapter.get_size(), 10)
    self.assertFalse(adapter.has_partial_batch())

  def test_batch_size(self):
    adapter = self.adapter_cls(
        self.tensor_input, self.tensor_target, batch_size=5)
    self.assertEqual(adapter.batch_size(), 5)

  def test_partial_batch(self):
    adapter = self.adapter_cls(
        self.tensor_input, self.tensor_target, batch_size=4)
    self.assertEqual(adapter.get_size(), 13)   # 50/4
    self.assertTrue(adapter.has_partial_batch())


class DatasetAdapterTest(DataAdapterTestBase):

  def setUp(self):
    super(DatasetAdapterTest, self).setUp()
    self.adapter_cls = data_adapter.DatasetAdapter

  def test_can_handle(self):
    self.assertFalse(self.adapter_cls.can_handle(self.numpy_input))
    self.assertFalse(self.adapter_cls.can_handle(self.tensor_input))
    self.assertTrue(self.adapter_cls.can_handle(self.dataset_input))
    self.assertFalse(self.adapter_cls.can_handle(self.generator_input))
    self.assertFalse(self.adapter_cls.can_handle(self.sequence_input))

  def test_training(self):
    dataset = self.adapter_cls(self.dataset_input).get_dataset()
    self.model.compile(loss='sparse_categorical_crossentropy', optimizer='sgd')
    self.model.fit(dataset)

  def test_size(self):
    adapter = self.adapter_cls(self.dataset_input)
    self.assertIsNone(adapter.get_size())

  def test_batch_size(self):
    adapter = self.adapter_cls(self.dataset_input)
    self.assertIsNone(adapter.batch_size())

  def test_partial_batch(self):
    adapter = self.adapter_cls(self.dataset_input)
    self.assertFalse(adapter.has_partial_batch())


class GeneratorDataAdapterTest(DataAdapterTestBase):

  def setUp(self):
    super(GeneratorDataAdapterTest, self).setUp()
    self.adapter_cls = data_adapter.GeneratorDataAdapter

  def test_can_handle(self):
    self.assertFalse(self.adapter_cls.can_handle(self.numpy_input))
    self.assertFalse(self.adapter_cls.can_handle(self.tensor_input))
    self.assertFalse(self.adapter_cls.can_handle(self.dataset_input))
    self.assertTrue(self.adapter_cls.can_handle(self.generator_input))
    self.assertFalse(self.adapter_cls.can_handle(self.sequence_input))

  def test_training(self):
    dataset = self.adapter_cls(self.generator_input).get_dataset()
    self.model.compile(loss='sparse_categorical_crossentropy', optimizer='sgd')
    self.model.fit(dataset)

  def test_size(self):
    adapter = self.adapter_cls(self.generator_input)
    self.assertIsNone(adapter.get_size())

  def test_batch_size(self):
    adapter = self.adapter_cls(self.generator_input)
    self.assertEqual(adapter.batch_size(), 5)

  def test_partial_batch(self):
    adapter = self.adapter_cls(self.generator_input)
    self.assertFalse(adapter.has_partial_batch())


class KerasSequenceAdapterTest(DataAdapterTestBase):

  def setUp(self):
    super(KerasSequenceAdapterTest, self).setUp()
    self.adapter_cls = data_adapter.KerasSequenceAdapter

  def test_can_handle(self):
    self.assertFalse(self.adapter_cls.can_handle(self.numpy_input))
    self.assertFalse(self.adapter_cls.can_handle(self.tensor_input))
    self.assertFalse(self.adapter_cls.can_handle(self.dataset_input))
    self.assertFalse(self.adapter_cls.can_handle(self.generator_input))
    self.assertTrue(self.adapter_cls.can_handle(self.sequence_input))

  def test_training(self):
    dataset = self.adapter_cls(self.sequence_input).get_dataset()
    self.model.compile(loss='sparse_categorical_crossentropy', optimizer='sgd')
    self.model.fit(dataset)

  def test_size(self):
    adapter = self.adapter_cls(self.sequence_input)
    self.assertEqual(adapter.get_size(), 10)

  def test_batch_size(self):
    adapter = self.adapter_cls(self.sequence_input)
    self.assertEqual(adapter.batch_size(), 5)

  def test_partial_batch(self):
    adapter = self.adapter_cls(self.sequence_input)
    self.assertFalse(adapter.has_partial_batch())


if __name__ == '__main__':
  test.main()

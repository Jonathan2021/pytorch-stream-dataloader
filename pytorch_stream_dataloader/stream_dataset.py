"""
Module that enables Parallel Multistreaming.

We define an IterableDataset that streams several iterables.

When fed to a Pytorch DataLoader with batch_size=None,
this streams batches from one worker at a time.
This has the effect of enabling parallel streaming.
"""
import random
import time
import torch
import numpy as np

from torch.utils.data import IterableDataset, DataLoader
from pytorch_stream_dataloader.utils import split_batch_size, split_dataset_sizes



class StreamDataset(IterableDataset):
    """Stream Dataset
    An Iterable Dataset zipping a group of iterables streams together.

    Args:
        stream_list (list): list of streams (path/ metadata)
        streamer (object): an iterator (user defined)
        batch_size (int): total batch size
        padding_mode (str): "zeros" "data" or "none", see "get_zip" function
        fill_value (object): padding value
    """
    def __init__(self, stream_list, streamer, batch_size, padding_mode, fill_value, pos, mutex):
        self.stream_list = stream_list
        self.batch_size = batch_size
        self.streamer = streamer
        self.padding_mode = padding_mode
        self.fill_value = fill_value
        assert padding_mode in ['zeros', 'data']
        if padding_mode == 'zeros':
            assert fill_value is not None
        self.pos = pos
        self.mutex = mutex

    def shuffle(self):
        random.shuffle(self.stream_list)

    def _set_seed(self):
        """ so that data is different along threads and epochs"""
        worker = torch.utils.data.get_worker_info()
        worker_id = int(worker.id) if worker is not None else 0
        seed = int(time.time()) + worker_id
        np.random.seed(seed)
        random.seed(seed)

    def __iter__(self):
        """Iterates over stream files

        Note: Here the scheduling of iterable is done at the beginning.
        Instead User can change this code to map lazily iterables.
        """
        self._set_seed()

        #initialization
        worker = torch.utils.data.get_worker_info()
        worker_id = int(worker.id) if worker is not None else 0
        stream_list = self.stream_list

        if worker_id == 0:
            random.shuffle(stream_list)

        num_workers = 1 if worker is None else worker.num_workers
        split_sizes = split_batch_size(self.batch_size, num_workers)
        worker = torch.utils.data.get_worker_info()
        worker_id = int(worker.id) if worker is not None else 0
        split_size = split_sizes[worker_id]

        if len(stream_list) < split_size:
            print('worker#', worker_id, ': Stopping... Number of streams < split_size')
            raise StopIteration

        """
        Just-in-time mapping
        The scheduling is done as we iterate.

        EDIT 9/7/2021: The position in the stream is shared accross workers
        This allows us to avoid the non ideal pre-iteration splitting of the dataset
        """
        def init_pos():
            self.mutex.acquire()
            self.pos.value = 0
            self.mutex.release()

        def increment_pos():
            self.mutex.acquire()
            pos = self.pos.value
            stream = stream_list[pos%len(stream_list)]
            new_pos = pos + 1
            self.pos.value = new_pos
            self.mutex.release()
            # debug
            # print("worker#", worker_id, " position : ", pos)
            return stream

        if worker_id == 0:
            init_pos()

        iterators = []
        for i in range(split_size):
            stream = increment_pos()
            stream = iter(self.streamer(stream))
            iterators.append(stream)

        actives = [1 for i in range(len(iterators))]
        num_actives = sum(actives)
        while num_actives:
            values = []
            for i, it in enumerate(iterators):
                try:
                    value = next(it)
                    assert value is not None
                except StopIteration:
                    stream = increment_pos()
                    actives[i] = 1 * (self.pos.value < len(stream_list))
                    if self.padding_mode == 'data' or actives[i]:
                        assert stream is not None, self.pos.value
                        iterators[i] = iter(self.streamer(stream))
                        value = next(iterators[i])
                    elif self.padding_mode == 'zeros':
                        value = self.fill_value

                values.append(value)
            yield tuple(values), worker_id
            num_actives = sum(actives)



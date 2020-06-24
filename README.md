# pytorch-streamloader

**The dataloader to stream videos or text or anything in temporally coherent batches.**

## What is it?

Current implementation of iterable dataset does not seem to cover well use-case of streaming several videos/ text/ audio in temporally coherent batches.
Here i provide a simple implementation of streaming with multiprocessing and pytorch.
This is mainly to get feedback and understand how to do this better :-) (but if you find this useful don't hesitate to give me feedback as well)

###ADD FIGURES

## Example of usage

A very simple example can be found in examples/text_dataset.py together with pytorch_stream_loader/text_stream_dataset.py

```
TEXTS = [
"".join([chr(j)+'_'+str(i)+";" for i in range(1000)])
for j in range(97, 97+27)
]
dataset = make_text_dataset(TEXTS)
```
What do we do here? We provide to the MultiStreamer class a class that can stream several text strings defined in TEXTS and it will stream them coherently:

#batch1:
========
a_0;a_1;a_2;
b_0;b_1;b_2;
c_0;c_1;c_2;
d_0;d_1;d_2;
e_0;e_1;e_2;
f_0;f_1;f_2;
g_0;g_1;g_2;
h_0;h_1;h_2;
#batch2:
========
a_3;a_4;a_5;
b_3;b_4;b_5;
c_3;c_4;c_5;
d_3;d_4;d_5;
e_3;e_4;e_5;
f_3;f_4;f_5;
g_3;g_4;g_5;
h_3;h_4;h_5;
#batch3:
========
a_3;a_4;a_5;
b_3;b_4;b_5;
c_3;c_4;c_5;
d_3;d_4;d_5;
e_3;e_4;e_5;
f_3;f_4;f_5;
g_3;g_4;g_5;
h_3;h_4;h_5;
...

How to make this streaming of text?
```
def make_text_dataset(
    words,
    num_iter=10,
    num_tbins=80,
    num_workers=1,
    batchsize=8,
    max_frames=100,
    start_epoch=0,
):
    array_dims = (num_tbins, 1)
    make_env = partial(
        TextStreams,
        stream_files=words,
        num_batches=num_iter,
        max_frames=max_frames,
        num_tbins=num_tbins,
    )
    dataset = MultiStreamer(
        make_env,
        array_dims,
        batchsize=batchsize,
        max_q_size=4,
        num_workers=num_workers,
        collate_fn=collate_fn,
        epoch=start_epoch,
        dtype=np.uint8,
        main_thread=0,
        pin_memory=0,
    )

    return dataset
```
Here we give the dataset generator (using partial) to the MultiStreamer, which is the main dataloader instanciating the threads (think of it as the Pytorch DataLoader). 
Here Each worker_id has its own "TextStreams" class that delivers "micro-batches" (Batchsize, Tbins, 1) that are collated into the Multistreamer.

Another Example:

You can run the video_dataset example on any folder containing .mp4! 
This should show you a grid of several videos being read at the same time and delivered with "minimal" latency to pytorch GPU. (well that is the idea at least). This indicates a timing around 1 ms to deliver a batch (because the main process is showing the frames and takes time on its own).

#todo put frames showcased here.







## Installation
TODO :-) 

import bisect
from typing import TYPE_CHECKING, List, Sequence

import av
import numpy as np

from ...extras.packages import is_pillow_available


if is_pillow_available():
    from PIL import Image


if TYPE_CHECKING:
    from av import Container
    from numpy.typing import NDArray
    from PIL.Image import Image as ImageObject
    from transformers import ProcessorMixin
    from transformers.image_processing_utils import BaseImageProcessor


def search_for_fit(numbers: Sequence[int], capacity: int) -> int:
    r"""
    Finds the index of largest number that fits into the knapsack with the given capacity.
    """
    index = bisect.bisect(numbers, capacity)
    return -1 if index == 0 else (index - 1)


def greedy_knapsack(numbers: List[int], capacity: int) -> List[List[int]]:
    r"""
    An efficient greedy algorithm with binary search for the knapsack problem.
    """
    numbers.sort()  # sort numbers in ascending order for binary search
    knapsacks = []

    while numbers:
        current_knapsack = []
        remaining_capacity = capacity

        while True:
            index = search_for_fit(numbers, remaining_capacity)
            if index == -1:
                break  # no more numbers fit in this knapsack

            remaining_capacity -= numbers[index]  # update the remaining capacity
            current_knapsack.append(numbers.pop(index))  # add the number to knapsack

        knapsacks.append(current_knapsack)

    return knapsacks


def get_pixel_values(images: Sequence["ImageObject"], processor: "ProcessorMixin", image_key: "str" = "pixel_values") -> "NDArray":
    r"""
    Processes visual inputs. (currently only supports a single image)
    """
    image_processor: "BaseImageProcessor" = getattr(processor, "image_processor")
    if len(images) <= 1:
        image = images[0] if len(images) != 0 else Image.new("RGB", (100, 100), (255, 255, 255))
        return image_processor(image, return_tensors="pt")[image_key][0]  # shape (C, H, W)
    else:
        return image_processor(images, return_tensors="pt")[image_key]  # shape (C, H, W)


def preprocess_video(
    video: "str"
)->"NDArray":
    container = av.open(video)
    total_frames = container.streams.video[0].frames
    indices = np.arange(0, total_frames, total_frames / 8).astype(int)
    clip = read_video_pyav(container, indices)
    return clip


def get_pixel_values_videos(
    videos: Sequence["str"], processor: "ProcessorMixin", video_key: "str" = "pixel_values_videos"
) -> "NDArray":
    image_processor: "BaseImageProcessor" = getattr(processor, "image_processor")
    if len(videos) == 1:
        clip = preprocess_video(videos[0])
        inputs = image_processor(videos=clip, padding=True, return_tensors="pt", images=None)[video_key][0]
        return inputs
    else:
        clips = []
        for video in videos:
            clip = preprocess_video(video)
            clips.append(clip)
        inputs = image_processor(videos=clips, padding=True, return_tensors="pt", images=None)[video_key]
        return inputs


def read_video_pyav(container: "Container", indices: "NDArray"):
    """
    Decode the video with PyAV decoder.

    Args:
        container (av.container.input.InputContainer): PyAV container.
        indices (List[int]): List of frame indices to decode.

    Returns:
        np.ndarray: np array of decoded frames of shape (num_frames, height, width, 3).
    """
    frames = []
    container.seek(0)
    start_index = indices[0]
    end_index = indices[-1]
    for i, frame in enumerate(container.decode(video=0)):
        if i > end_index:
            break
        if i >= start_index and i in indices:
            frames.append(frame)
    return np.stack([x.to_ndarray(format="rgb24") for x in frames])


def get_paligemma_token_type_ids(input_len: int, processor: "ProcessorMixin") -> List[int]:
    r"""
    Gets paligemma token type ids for computing loss.
    """
    image_seq_length = getattr(processor, "image_seq_length")
    return [0] * image_seq_length + [1] * (input_len - image_seq_length)
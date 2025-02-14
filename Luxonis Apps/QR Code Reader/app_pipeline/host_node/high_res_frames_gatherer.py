import logging as log

import cv2
import depthai as dai
import numpy as np
import robothub as rh

from app_pipeline import host_node, messages, script_node
from node_helpers import FindStart

__all__ = ["HighResFramesGatherer"]


class HighResFramesGatherer(host_node.BaseNode):
    """Add cr code text to qr bounding boxes."""
    # the overlap percentage is for some reason different to the one in the script node

    def __init__(self, input_node: host_node.BaseNode):
        super().__init__()
        input_node.set_callback(callback=self.__callback)
        self._target_image_count = rh.CONFIGURATION["crop_count"]
        self._find_start = FindStart(sequence_length=self._target_image_count)
        self._frames = []
        self._current_sequence_number = -1
        self._current_image_count = 0
        self._OVERLAP = rh.CONFIGURATION["merged_image_overlap"]

    @rh.decorators.measure_average_performance(report_every_minutes=1)
    def __callback(self, frame: dai.ImgFrame):
        # if not self._find_start(frame):
        #     return
        new_sequence_number = frame.getSequenceNum()

        if new_sequence_number != self._current_sequence_number:
            self._current_sequence_number = new_sequence_number
            self._current_image_count = 0
            self._frames.clear()

        self._frames.append(frame)
        self._current_image_count += 1

        if self._current_image_count == self._target_image_count:
            merged_frame: np.ndarray = self._reconstruct_whole_frame()
            message = messages.HighResFrame(frame=merged_frame, sequence_number=self._current_sequence_number)
            self.send_message(message=message)

    def _reconstruct_whole_frame(self) -> np.ndarray:
        image1 = self._frames[0].getCvFrame()
        image2 = self._frames[1].getCvFrame()
        image3 = self._frames[2].getCvFrame()
        image4 = self._frames[3].getCvFrame()
        image5 = self._frames[4].getCvFrame()
        image6 = self._frames[5].getCvFrame()
        image7 = self._frames[6].getCvFrame()
        image8 = self._frames[7].getCvFrame()
        image9 = self._frames[8].getCvFrame()
        # cv2.imshow("image1", image1)
        # cv2.imshow("image2", image2)
        # cv2.imshow("image3", image3)
        # cv2.imshow("image4", image4)
        # cv2.imshow("image5", image5)
        # cv2.imshow("image6", image6)
        # cv2.imshow("image7", image7)
        # cv2.imshow("image8", image8)
        # cv2.imshow("image9", image9)

        image_width = image1.shape[1]
        image_height = image1.shape[0]
        overlap_width = int(image_width * self._OVERLAP)
        overlap_height = int(image_height * self._OVERLAP)

        merged_image_width = 3 * image_width - 2 * overlap_width
        merged_image_height = 3 * image_height - 2 * overlap_height

        merged_image = np.zeros((merged_image_height, merged_image_width, 3), dtype=np.uint8)

        # draw the situation to understand this
        merged_image[: image_height, : image_width] = image1
        merged_image[image_height - overlap_height: image_height * 2 - overlap_height, : image_width] = image2
        merged_image[image_height * 2 - 2 * overlap_height: image_height * 3 - 2 * overlap_height, : image_width] = image3
        merged_image[: image_height, image_width - overlap_width: image_width * 2 - overlap_width] = image4
        merged_image[image_height - overlap_height: image_height * 2 - overlap_height,
        image_width - overlap_width: image_width * 2 - overlap_width] = image5
        merged_image[image_height * 2 - 2 * overlap_height: image_height * 3 - 2 * overlap_height,
        image_width - overlap_width: image_width * 2 - overlap_width] = image6
        merged_image[: image_height, image_width * 2 - 2 * overlap_width: image_width * 3 - 2 * overlap_width] = image7
        merged_image[image_height - overlap_height: image_height * 2 - overlap_height, image_width * 2 - 2 * overlap_width: image_width * 3 - 2 * overlap_width] = image8
        merged_image[image_height * 2 - 2 * overlap_height: image_height * 3 - 2 * overlap_height, image_width * 2 - 2 * overlap_width: image_width * 3 - 2 * overlap_width] = image9
        return merged_image






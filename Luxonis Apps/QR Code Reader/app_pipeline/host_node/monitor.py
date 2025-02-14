import cv2
import robothub as rh

from app_pipeline import host_node
from app_pipeline.messages import FramesWithDetections

__all__ = ["Monitor"]


class Monitor(host_node.BaseNode):
    def __init__(self, input_node: host_node.BaseNode, name: str):
        super().__init__()
        input_node.set_callback(callback=self.__callback)
        self.name = name
        self._live_view = rh.DepthaiLiveView(name="Preview Live View", unique_key=rh.DEVICE_MXID, width=rh.CONFIGURATION["encoder_frame_width"],
                                             height=rh.CONFIGURATION["encoder_frame_height"],
                                             device_mxid=rh.DEVICE_MXID)

    @rh.decorators.measure_call_frequency
    def __callback(self, message: FramesWithDetections):
        if rh.LOCAL_DEV:
            self._local_monitor(message)
        else:
            self._remote_monitor(message)

    def _local_monitor(self, message: FramesWithDetections):
        img = message.high_res_rgb.frame
        bboxes = message.qr_bboxes.bounding_boxes
        for bbox in bboxes:
            label = f"{bbox.label}, {bbox.confidence:.2f}"
            # draw bounding box
            cv2.rectangle(img, (bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax), color=(0, 0, 255), thickness=2)
            # draw label
            cv2.putText(img, label, (bbox.xmin, bbox.ymin - 1), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2)
        cv2.imshow(self.name, img)
        cv2.waitKey(1)

    def _remote_monitor(self, message: FramesWithDetections):
        h264_frame = message.h264_frame.getCvFrame()
        bboxes = message.qr_bboxes.bounding_boxes
        for bbox in bboxes:
            self._live_view.add_rectangle(bbox.transform(width=rh.CONFIGURATION["encoder_frame_width"],
                                                         height=rh.CONFIGURATION["encoder_frame_height"]), label=bbox.label)
        self._live_view.publish(h264_frame=h264_frame)

import logging as log

import depthai as dai
import robothub as rh
from app_pipeline import host_node
from app_pipeline.oak_pipeline import create_pipeline


class Application(rh.BaseDepthAIApplication):
    image_event_switch: host_node.Switch
    on_demand_video_switch: host_node.Switch
    video_5_min_switch: host_node.Switch
    video_buffer_5_minutes: host_node.VideoBuffer
    image_event: host_node.ImageEvent
    monitor: host_node.Monitor
    rgb_control: dai.DataInputQueue

    def __init__(self):
        super().__init__()

        rh.COMMUNICATOR.on_frontend(
            notification=self.on_fe_notification,
            request=self.on_fe_request,
        )

    def setup_pipeline(self) -> dai.Pipeline:
        """Define the pipeline using DepthAI."""

        log.info(f"App config: {rh.CONFIGURATION}")
        pipeline = dai.Pipeline()
        create_pipeline(pipeline=pipeline)
        return pipeline

    def manage_device(self, device: dai.Device):
        log.info(f"{device.getMxId()} creating output queues...")
        h264_node = host_node.Bridge(device=device, out_name="main_h264", blocking=True)
        mjpeg_node = host_node.Bridge(device=device, out_name="main_mjpeg", blocking=True)

        self.video_5_min_switch = host_node.Switch(input_node=h264_node, name="video_5_min_switch")
        self.on_demand_video_switch = host_node.Switch(input_node=h264_node, name="on_demand_video_switch")
        configurable_buffer_switch = host_node.Switch(input_node=h264_node, name="configurable_buffer_switch")
        self.image_event_switch = host_node.Switch(input_node=mjpeg_node, name="image_event_switch")

        # self.video_recording = host_node.VideoRecording(input_node=h264_node)
        on_demand_video = host_node.VideoBuffer(input_node=self.on_demand_video_switch, buffer_size_minutes=5)
        self.video_buffer_5_minutes = host_node.VideoBuffer(input_node=self.video_5_min_switch, buffer_size_minutes=5)
        configurable_video_buffer = host_node.VideoBuffer(input_node=configurable_buffer_switch,
                                                          buffer_size_minutes=rh.CONFIGURATION["video_buffer_size_minutes"])

        regular_video_event = host_node.RegularEvent(input_node=configurable_video_buffer, name="regular_video_event",
                                                     frequency_seconds=rh.CONFIGURATION["video_event_frequency_minutes"] * 60)
        regular_image_event = host_node.RegularEvent(input_node=mjpeg_node, name="regular_image_event",
                                                     frequency_seconds=rh.CONFIGURATION["image_event_frequency_minutes"] * 60)

        host_node.VideoEvent(input_node=self.video_buffer_5_minutes)
        host_node.VideoEvent(input_node=on_demand_video)

        host_node.VideoEvent(input_node=regular_video_event)
        host_node.ImageEvent(input_node=regular_image_event)
        host_node.ImageEvent(input_node=self.image_event_switch)

        self.monitor = host_node.Monitor(input_node=h264_node)

        configurable_buffer_switch.passthrough_on()  # keep always on
        self.video_5_min_switch.switch_on()
        self.on_demand_video_switch.switch_off()

        self.rgb_control = device.getInputQueue(name="rgb_control")

        log.info(f"{device.getMxId()} Application started")
        host_node.Bridge.run(device_stop_event=self._device_stop_event)

    def on_fe_notification(self, session_id, unique_key, payload):
        log.info(f"{payload = } {unique_key=}")
        if unique_key == 'recording_start':
            self.on_demand_video_switch.switch_on()
            self.monitor.toggle_recording_on()
        elif unique_key == 'recording_stop':
            self.on_demand_video_switch.switch_off()
            self.monitor.toggle_recording_off()
        elif unique_key == 'send_video_buffer':
            self.video_5_min_switch.flick_switch()
            self.video_buffer_5_minutes.clear_buffers()
        elif unique_key == 'send_image_event':
            self.image_event_switch.flick_switch()

    def on_fe_request(self, session_id, unique_key, payload):
        log.info(f"FE request: {unique_key = }")

    def on_configuration_changed(self, configuration_changes: dict) -> None:
        log.info(f"CONFIGURATION CHANGES: {configuration_changes}")
        require_restart = ["fps", "resolution", "video_buffer_size_minutes", "video_event_frequency_minutes", "image_event_frequency_minutes",
                           "auto_exposure_limit", "flip_camera"]
        for key in require_restart:
            if key in configuration_changes:
                log.info(f"{key} change needs a new pipeline. Restarting OAK device...")
                self.restart_device()
        if (("manual_exposure" in configuration_changes or "manual_iso" in configuration_changes or
             "enable_manual_exposure" in configuration_changes) and rh.CONFIGURATION["enable_manual_exposure"]):
            log.info(f"Setting manual exposure to {rh.CONFIGURATION['manual_exposure']} and iso to {rh.CONFIGURATION['manual_iso']}")
            ctrl = dai.CameraControl()
            ctrl.setManualExposure(rh.CONFIGURATION["manual_exposure"], rh.CONFIGURATION["manual_iso"])
            self.rgb_control.send(ctrl)
        if "enable_manual_exposure" in configuration_changes and not rh.CONFIGURATION["enable_manual_exposure"]:
            ctrl = dai.CameraControl()
            ctrl.setAutoExposureEnable()
            self.rgb_control.send(ctrl)
        if "manual_focus" in configuration_changes and rh.CONFIGURATION["manual_focus"] > 0:
            log.info(f"Setting manual focus to {rh.CONFIGURATION['manual_focus']}")
            ctrl = dai.CameraControl()
            ctrl.setManualFocus(rh.CONFIGURATION["manual_focus"])
            self.rgb_control.send(ctrl)


if __name__ == "__main__":
    app = Application()
    app.run()

# -*- coding: future_fstrings -*-
from define import ResolveEvent
from reference import process
from setting import Setting
from flows import flow_pipeline


class ResolveProcess():
    def __init__(
        self, frame, alicevision_path, aruco_path, shot_path, job_path, cali_path,
        resolve_steps, ignore_flows=[], solo_flows=[], gpu_core=-1,
    ):
        process.set(self)

        self._setting = Setting(
            frame, alicevision_path, aruco_path, shot_path, job_path, cali_path,
            resolve_steps, gpu_core
        )

        self._flows = self._build_flows(ignore_flows, solo_flows)
        self._callbacks = []
        self._is_fail = False

    @property
    def setting(self):
        return self._setting

    def _build_flows(self, ignore_flows, solo_flows):
        this_flow_list = []

        if self._setting.resolve_steps is not None:
            for step in self._setting.resolve_steps:
                for flow in flow_pipeline[step]:
                    if (
                        (len(solo_flows) > 0 and flow not in solo_flows) or
                        (
                            len(ignore_flows) > 0 and
                            flow in ignore_flows and
                            flow not in solo_flows
                        )
                    ):
                        continue

                    this_flow_list.append(flow())

        return this_flow_list

    def _update_progress(self, progress):
        self.dispatch_event(ResolveEvent.PROGRESS, progress)

    def run(self):
        progress = 0.0
        progress_segment = 100.0 / len(self._flows)
        for flow in self._flows:
            flow.run()

            if self._is_fail:
                return

            progress += progress_segment
            self._update_progress(progress)

        self.complete()

    def on_event_emit(self, func):
        self._callbacks.append(func)

    def dispatch_event(self, event, payload=None):
        for func in self._callbacks:
            func(event, payload)

    def fail(self, message):
        self.dispatch_event(ResolveEvent.FAIL, message)
        self._is_fail = True

    def log_info(self, message):
        self.dispatch_event(ResolveEvent.LOG_INFO, message)

    def log_cmd(self, message):
        self.dispatch_event(ResolveEvent.LOG_STDOUT, message)

    def log_warning(self, message):
        self.dispatch_event(ResolveEvent.LOG_WARNING, message)

    def complete(self):
        self.dispatch_event(ResolveEvent.COMPLETE)

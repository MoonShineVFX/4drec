# -*- coding: future_fstrings -*-
from process import ResolveProcess
from define import ResolveEvent


class LocalResolver():
    def __init__(
        self, frame, alicevision_path, aruco_path, shot_path, job_path, cali_path,
        resolve_steps, ignore_flows, solo_flows
    ):
        self._process = ResolveProcess(
            frame, alicevision_path, aruco_path, shot_path, job_path, cali_path,
            resolve_steps, ignore_flows, solo_flows
        )

        self._process.on_event_emit(self._on_event_emit)
        self._process.run()

    def _on_event_emit(self, event, payload):
        if event is ResolveEvent.COMPLETE:
            print('> Complete!!')
        elif event is ResolveEvent.FAIL:
            print(f'> FAIL: {payload}')
        elif event is ResolveEvent.LOG_INFO:
            print(f'INFO: {payload}')
        elif event is ResolveEvent.LOG_STDOUT:
            print(f'STDO: {payload}')
        elif event is ResolveEvent.LOG_WARNING:
            print(f'WARN: {payload}')
        elif event is ResolveEvent.PROGRESS:
            print(f'Progress: {payload:.2f}%')

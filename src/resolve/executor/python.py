# -*- coding: future_fstrings -*-
from process import ResolveProcess
from define import ResolveEvent
from flows import flow_dict


class PythonResolver():
    def __init__(
        self, frame, shot_path, job_path, cali_path, python_flow, setting
    ):
        self._process = ResolveProcess(
            frame, None, None, shot_path, job_path, cali_path, [], []
        )

        self._process.on_event_emit(self._on_event_emit)
        self._process.setting.from_json(setting)

        flow_dict[python_flow]().run_python()
        self._process.complete()

    def _on_event_emit(self, event, payload):
        if event is ResolveEvent.COMPLETE:
            print('python | Complete!!')
        elif event is ResolveEvent.FAIL:
            print(f'python | FAIL: {payload}')
        elif event is ResolveEvent.LOG_INFO:
            print(f'python | {payload}')
        elif event is ResolveEvent.LOG_STDOUT:
            print(f'python | {payload}')
        elif event is ResolveEvent.LOG_WARNING:
            print(f'python | WARN: {payload}')
        elif event is ResolveEvent.PROGRESS:
            print(f'python | Progress: {payload:.2f}%')

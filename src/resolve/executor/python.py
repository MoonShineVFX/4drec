# -*- coding: future_fstrings -*-
from process import ResolveProcess
from define import ResolveEvent
from flows import flow_dict


class PythonResolver():
    def __init__(
        self, frame, shot_path, job_path, cali_path, python_flow
    ):
        self._process = ResolveProcess(
            frame, None, None, shot_path, job_path, cali_path, [], []
        )

        self._process.on_event_emit(self._on_event_emit)

        flow_dict[python_flow]().run_python()
        self._process.complete()

    def _on_event_emit(self, event, payload):
        if event is ResolveEvent.COMPLETE:
            print('python27 | Complete!!')
        elif event is ResolveEvent.FAIL:
            print(f'python27 | FAIL: {payload}')
        elif event is ResolveEvent.LOG_INFO:
            print(f'python27 | {payload}')
        elif event is ResolveEvent.LOG_STDOUT:
            print(f'python27 | {payload}')
        elif event is ResolveEvent.LOG_WARNING:
            print(f'python27 | WARN: {payload}')
        elif event is ResolveEvent.PROGRESS:
            print(f'python27 | Progress: {payload:.2f}%')

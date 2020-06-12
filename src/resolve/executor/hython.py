# -*- coding: future_fstrings -*-
from process import ResolveProcess
from define import ResolveEvent
from flows import flow_dict


class HythonResolver():
    def __init__(
        self, frame, job_path, hython_flow
    ):
        self._process = ResolveProcess(
            frame, None, job_path, None, [], []
        )
        self._process.on_event_emit(self._on_event_emit)

        flow_dict[hython_flow]().run_hython()
        self._process.complete()

    def _on_event_emit(self, event, payload):
        if event is ResolveEvent.COMPLETE:
            print('hython | Complete!!')
        elif event is ResolveEvent.FAIL:
            print(f'hython | FAIL: {payload}')
        elif event is ResolveEvent.LOG_INFO:
            print(f'hython | {payload}')
        elif event is ResolveEvent.LOG_STDOUT:
            print(f'hython | {payload}')
        elif event is ResolveEvent.LOG_WARNING:
            print(f'hython | WARN: {payload}')
        elif event is ResolveEvent.PROGRESS:
            print(f'hython | Progress: {payload:.2f}%')

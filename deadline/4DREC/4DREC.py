from System import *
from System.Diagnostics import *
from System.IO import *

from Deadline.Plugins import *
from Deadline.Scripting import *

import launch
from process import ResolveProcess
from define import ResolveEvent, ResolveStep
from flows import flow_dict


def GetDeadlinePlugin():
    """get 4DREC plugin"""
    return FourDRecPlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    """flush memory"""
    deadlinePlugin.Cleanup()


class FourDRecPlugin(DeadlinePlugin):
    """4DREC Plugin"""

    def __init__(self):
        self.InitializeProcessCallback += self.InitializeProcess
        self.StartJobCallback += self.StartJob
        self.RenderTasksCallback += self.RenderTasks
        self._process = None

    def Cleanup(self):
        """flush memory"""
        del self.InitializeProcessCallback
        del self.StartJobCallback
        del self.RenderTasksCallback

    def InitializeProcess(self):
        """initialize process"""
        self.SingleFramesOnly = False
        self.PluginType = PluginType.Advanced

    def StartJob(self):
        """prepare resolve"""
        return

    def RenderTasks(self):
        """render"""
        job = self.GetJob()
        shot_path = job.GetJobExtraInfoKeyValue('shot_path')
        job_path = job.GetJobExtraInfoKeyValue('job_path')
        cali_path = job.GetJobExtraInfoKeyValueWithDefault('cali_path', None)
        resolve_step = job.GetJobExtraInfoKeyValue('resolve_step')

        gpu_core = -1
        if self.OverrideGpuAffinity():
            gpu_core = self.GpuAffinity()[0]

        ignore_flows = job.GetJobExtraInfoKeyValueWithDefault(
            'ignore_flows', None
        )
        solo_flows = job.GetJobExtraInfoKeyValueWithDefault(
            'solo_flows', None
        )

        if ignore_flows is not None:
            ignore_flows = [
                flow_dict[flow_str] for flow_str in ignore_flows.split(',')
            ]
        else:
            ignore_flows = []

        if solo_flows is not None:
            solo_flows = [
                flow_dict[flow_str] for flow_str in solo_flows.split(',')
            ]
        else:
            solo_flows = []

        self._process = ResolveProcess(
            frame=self.GetStartFrame(),
            alicevision_path='Q:\\4DREC\\alicevision\\',
            aruco_path='Q:\\4DREC\\aruco\\',
            shot_path=shot_path,
            job_path=job_path,
            cali_path=cali_path,
            resolve_steps=[ResolveStep(resolve_step)],
            ignore_flows=ignore_flows,
            solo_flows=solo_flows,
            gpu_core=gpu_core
        )

        for pname in self._process.setting.get_parameters():
            value = job.GetJobExtraInfoKeyValueWithDefault(pname, None)
            if value is None:
                continue
            self._process.setting.apply_parameter(pname, value)

        self._process.on_event_emit(self._on_event_emit)
        self._process.run()

    def _on_event_emit(self, event, payload):
        if event is ResolveEvent.COMPLETE:
            self.ExitWithSuccess()
        elif event is ResolveEvent.FAIL:
            self.FailRender(payload)
        elif event is ResolveEvent.LOG_INFO:
            self.LogInfo(payload)
        elif event is ResolveEvent.LOG_STDOUT:
            self.LogStdout(payload)
        elif event is ResolveEvent.LOG_WARNING:
            self.LogWarning(payload)
        elif event is ResolveEvent.PROGRESS:
            self.SetProgress(payload)

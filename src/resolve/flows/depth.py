# -*- coding: future_fstrings -*-
from reference import process

from .flow import Flow, FlowCommand
from .feature import ClipLandmarks, PrepareDenseScene


class DepthMapEstimation(Flow):
    def __init__(self):
        super(DepthMapEstimation, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_depthMapEstimation'
            ),
            args={
                'input': ClipLandmarks.get_file_path('sfm'),
                'imagesFolder': PrepareDenseScene.get_folder_path(),
                'output': self.get_folder_path(),
            },
            override=self.get_parameters()
        )

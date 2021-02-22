from mpegdash.nodes import MPEGDASH, Period, AdaptationSet
from mpegdash.parser import MPEGDASHParser
from copy import deepcopy
from threading import Thread, Event
import os
import time
import shutil

from utility.setting import setting


CAMERA_COUNT = len(setting.get_working_camera_ids())


class MPDModifier(Thread):
    def __init__(self, input_path):
        super().__init__()
        self._stop_event = Event()

        self._input_path = input_path
        self._output_path = str(setting.get_stream_path() / 'main.mpd.tmp')
        self._real_path = str(setting.get_stream_path() / 'main.mpd')
        self._bak_path = str(setting.get_stream_path() / 'main.mpd.bak')

    def _make_mpd(self):
        try:
            with open(self._input_path, 'r') as f:
                data = f.read()
        except PermissionError as e:
            return

        mpd: MPEGDASH = MPEGDASHParser.parse(data)
        period: Period = mpd.periods[0]
        ref_adaptation_set: AdaptationSet = period.adaptation_sets[0]
        ref_segment_template = ref_adaptation_set.representations[0].segment_templates[0]
        ref_segment_template.media = '$RepresentationID$/' + ref_segment_template.media
        ref_segment_template.initialization = '$RepresentationID$/' + ref_segment_template.initialization

        new_adaptation_set = []
        for i in range(CAMERA_COUNT):
            this_id = i + 1
            new_adaptation = deepcopy(ref_adaptation_set)
            new_adaptation.id = this_id
            new_adaptation.representations[0].id = this_id
            new_adaptation_set.append(new_adaptation)

        period.adaptation_sets = new_adaptation_set

        # save
        MPEGDASHParser.write(mpd, self._output_path)
        if os.path.isfile(self._real_path):
            shutil.move(self._real_path, self._bak_path)
        shutil.move(self._output_path, self._real_path)

    def run(self):
        while not os.path.isfile(self._input_path):
            time.sleep(1)

        while not self.is_stop():
            self._make_mpd()
            time.sleep(1)

    def stop(self):
        self._stop_event.set()

    def is_stop(self):
        return self._stop_event.is_set()
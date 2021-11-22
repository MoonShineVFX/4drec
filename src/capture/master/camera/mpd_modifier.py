from mpegdash.nodes import MPEGDASH, Period, AdaptationSet
from mpegdash.parser import MPEGDASHParser
from copy import deepcopy
from threading import Thread, Event
import os
import time
import shutil

from utility.setting import setting


CAMERA_COUNT = len(setting.get_working_camera_ids())
STREAM_PATH = str(setting.get_stream_path()).replace('Q:\\', 'D:\\storage\\')


class MPDModifier(Thread):
    def __init__(self):
        super().__init__()
        self._stop_event = Event()

        self._output_path = STREAM_PATH + '\\main.mpd.tmp'
        self._real_path = STREAM_PATH + '\\main.mpd'
        self._bak_path = STREAM_PATH + '\\main.mpd.bak'

        self._master_camera_num = None

        self.start()

    def _make_mpd(self):
        if self._master_camera_num is None:
            mpd_list = []
            try:
                for i in range(CAMERA_COUNT):
                    with open(f'{STREAM_PATH}\\{i + 1}\\origin.mpd', 'r') as f:
                        data = f.read()
                    mpd_list.append(MPEGDASHParser.parse(data))
            except PermissionError as e:
                print(e)
                return
            except FileNotFoundError as e:
                print(e)
                return

            master_mpd_num = None
            start_number = None

            for idx, mpd in enumerate(mpd_list):
                period: Period = mpd.periods[0]
                ref_adaptation_set: AdaptationSet = period.adaptation_sets[0]
                ref_segment_template = ref_adaptation_set.representations[0].segment_templates[0]
                this_start_number = ref_segment_template.start_number
                if start_number is None or this_start_number < start_number:
                    master_mpd_num = idx + 1

            self._master_camera_num = master_mpd_num

        try:
            with open(f'{STREAM_PATH}\\{self._master_camera_num}\\origin.mpd', 'r') as f:
                data = f.read()
        except PermissionError as e:
            print(e)
            return
        except FileNotFoundError as e:
            print(e)
            return
        output_mpd = self.build_master_mpd(data)

        # save
        MPEGDASHParser.write(output_mpd, self._output_path)
        if os.path.isfile(self._real_path):
            shutil.move(self._real_path, self._bak_path)
        shutil.move(self._output_path, self._real_path)

    def build_master_mpd(self, data):
        mpd = MPEGDASHParser.parse(data)
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
        return mpd

    def run(self):
        while not self.is_stop():
            self._make_mpd()
            time.sleep(1)

    def stop(self):
        self._stop_event.set()

    def is_stop(self):
        return self._stop_event.is_set()
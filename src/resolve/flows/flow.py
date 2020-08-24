# -*- coding: future_fstrings -*-
import os
import shutil
import subprocess
import time
import sys
if sys.version_info[0] < 3:
    from pathlib2 import Path
else:
    from pathlib import Path

from reference import process


class Flow(object):
    _file = {}

    def __init__(self, no_folder=False, skip_clean_folder=False):
        self._no_folder = no_folder
        self._skip_clean_folder = skip_clean_folder

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def get_folder_path(cls):
        return f'{process.setting.frame_path}{cls.get_name()}/'

    @classmethod
    def get_file_path(cls, name):
        return cls.get_folder_path() + cls._file[name]

    @classmethod
    def get_file_path_with_folder(cls, name, folder):
        return f'{folder}{cls.get_name()}/' + cls._file[name]

    def run(self):
        process.log_info(f'\n> Flow [{self.get_name()}] Start')

        # folder
        if not self._no_folder:
            if not self._skip_clean_folder:
                self._clean_folder()

            def make_folder():
                Path(self.get_folder_path()).mkdir(parents=True, exist_ok=True)

            try:
                make_folder()
            except WindowsError:
                process.log_info('Create folder error, wait 3 secs.')
                time.sleep(3)
                make_folder()

        Path(process.setting.export_path).mkdir(parents=True, exist_ok=True)

        # run
        self._run()

        process.log_info(f'> Flow [{self.get_name()}] Done')

    @classmethod
    def _clean_folder(cls):
        if os.path.isdir(cls.get_folder_path()):
            process.log_info('Output folder already exists, clean it.')
            shutil.rmtree(cls.get_folder_path())
            while os.path.exists(cls.get_folder_path()):
                pass

    @classmethod
    def clean_cache(cls, *args):
        process.log_info(f'> Clean flow: {cls.get_name()}')
        import glob
        import os
        files = []
        for ext in args:
            files.extend(
                glob.glob(
                    cls.get_folder_path() +
                    ext
                )
            )

        for f in files:
            os.remove(f)

    def _make_command(self):
        return None

    def _check_force_quit(self, line):
        return False

    def _run(self):
        command = self._make_command()
        if command is None:
            return

        command_list = command.to_list()

        process.log_info(f'Command: {command_list}')
        cmd = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            env=process.setting.get_environment()
        )

        force_quit = False
        for line in iter(cmd.stdout.readline, b''):
            try:
                line = line.decode('utf-8').rstrip()
            except:
                line = line.decode('cp950').rstrip()
            process.log_cmd(line)
            force_quit = self._check_force_quit(line)
            if force_quit:
                process.log_warning('Force QUIT!')
                cmd.kill()
                break

        return_code = cmd.wait()
        if return_code != 0 and not force_quit:
            error_log = (
                f'Return Code: {return_code}\n'
                f'Error Workflow: {self.get_name()}'
            )
            process.log_warning(error_log)
            process.fail(error_log)


class HythonFlow(Flow):
    def __init__(self, no_folder=False, skip_clean_folder=False):
        super(HythonFlow, self).__init__(no_folder, skip_clean_folder)

    def _make_command(self):
        return FlowCommand(
            execute=process.setting.houdini_execute,
            args={
                '': f'{os.getcwd()}/launch.py',
                'executor': 'hython',
                'frame': process.setting.frame,
                'shot_path': process.setting.shot_path,
                'job_path': process.setting.job_path,
                'hython_flow': self.get_name()
            }
        )

    def run_hython(self):
        return


class PythonFlow(Flow):
    def __init__(self, no_folder=False, skip_clean_folder=False):
        super(PythonFlow, self).__init__(no_folder, skip_clean_folder)

    def _make_command(self):
        return FlowCommand(
            execute=process.setting.get_python_executable_path(),
            args={
                'executor': 'python',
                'frame': process.setting.frame,
                'shot_path': process.setting.shot_path,
                'job_path': process.setting.job_path,
                'cali_path': process.setting.cali_path,
                'python_flow': self.get_name()
            }
        )

    def run_python(self):
        return


class FlowCommand(object):
    def __init__(self, execute, args):
        self._execute = execute
        self._args = args

    @property
    def execute(self):
        return self._execute

    @property
    def args(self):
        return self._args

    def to_list(self):
        command_list = [self._execute]

        if isinstance(self._args, dict):
            for key, value in self._args.items():
                command_list.append('--' + key)
                command_list.append(str(value))
        else:
            for arg in self._args:
                command_list.append(str(arg))

        return command_list

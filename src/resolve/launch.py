import os
directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(directory)
import sys
sys.path.insert(1, directory)
sys.path.insert(1, directory + '\\module')

import future_fstrings
future_fstrings.register()


if __name__ == '__main__':
    import argparse
    from define import ResolveStep
    from flows import flow_dict
    from executor import LocalResolver, HythonResolver, PythonResolver

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-e', '--executor', type=str,
        help='Executor for resolve, default: local',
        choices=['local', 'hython', 'python'],
        default='local'
    )
    parser.add_argument(
        '-f', '--frame', type=int, help='Frame number to resolve'
    )
    parser.add_argument(
        '-a', '--alicevision_path', type=str,
        help='alicevision program path, default: c:/alicevision/',
        default='c:/alicevision/'
    )
    parser.add_argument(
        '-s', '--shot_path', type=str,
        help='recorded shot path'
    )
    parser.add_argument(
        '-j', '--job_path', type=str,
        help='resolve job path'
    )
    parser.add_argument(
        '-aruco', '--aruco_path', type=str,
        help='aruco calibration program path, default: //storage03/cache/4DREC/aruco/',
        default='//storage03/cache/4DREC/aruco/'
    )
    parser.add_argument(
        '-c', '--cali_path', type=str,
        help='calibration reference path',
        default=None
    )
    parser.add_argument(
        '-r', '--resolve_steps', type=str, nargs='*',
        help='Resolve steps to process',
        choices=['feature', 'calibrate', 'sfm', 'depth', 'mesh'],
        default=['feature', 'calibrate', 'sfm', 'depth', 'mesh']
    )
    parser.add_argument(
        '-ig', '--ignore_flows', type=str, nargs='*',
        help='flows to ignore from steps',
        choices=flow_dict.keys(),
        default=[]
    )
    parser.add_argument(
        '-so', '--solo_flows', type=str, nargs='*',
        help='flows to solo from steps',
        choices=flow_dict.keys(),
        default=[]
    )
    parser.add_argument(
        '-hou', '--hython_flow', type=str,
        help='flow to process with hython',
        choices=flow_dict.keys(),
    )
    parser.add_argument(
        '-pyt', '--python_flow', type=str,
        help='flow to process with python27',
        choices=flow_dict.keys(),
    )

    args = parser.parse_args()

    args.resolve_steps = [ResolveStep(s) for s in args.resolve_steps]
    args.ignore_flows = [flow_dict[f] for f in args.ignore_flows]
    args.solo_flows = [flow_dict[f] for f in args.solo_flows]

    if args.cali_path == 'None' or args.cali_path == '':
        args.cali_path = None

    for attr in ('shot_path', 'job_path', 'cali_path', 'alicevision_path'):
        path = getattr(args, attr)

        if path is None:
            continue

        if not path.endswith('/'):
            setattr(args, attr, path + '/')

    if args.executor == 'local':
        solver = LocalResolver
    elif args.executor == 'hython':
        solver = HythonResolver
    elif args.executor == 'python':
        solver = PythonResolver

    kwargs = {}
    for name in solver.__init__.__code__.co_varnames:
        if name == 'self':
            continue

        attr = getattr(args, name)
        if attr is None and name != 'cali_path':
            raise ValueError("[{}] must be set".format(name))

        kwargs[name] = attr

    solver(**kwargs)

import os


os.environ.update({
    'cali_path': r'Q:\shots\5fa4c3f1318496d390b56948',
    'shot_path': r'Q:\shots\5fa4c479318496d390b56949',
    'job_path': r'Q:\metadata\job',
    'start_frame': '5981',
    'end_frame': '6011',
    'current_frame': '5998'
})

if __name__ == '__main__':
    from common.metashape_manager import MetashapeProject

    project = MetashapeProject()
    # project.initial()
    # project.calibrate()
    # project.resolve()

    # for f in range(5981, 6012):
    #     print(f'=================== {f} =================== ')
    #     os.environ['current_frame'] = str(f)
    #     project = MetashapeProject()
    #     project.resolve()

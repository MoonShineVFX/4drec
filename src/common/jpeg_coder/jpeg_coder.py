from pathlib import Path
from turbojpeg import TurboJPEG, TJPF_RGB

jpeg_coder = TurboJPEG(
    str(Path(__file__).parent / 'turbojpeg.dll')
)

from pathlib import Path
from turbojpeg import TurboJPEG

jpeg_coder = TurboJPEG(
    str(Path(__file__).parent / 'turbojpeg.dll')
)

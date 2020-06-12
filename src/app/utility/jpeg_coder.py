"""Turbo JPEG 模組

高速處理編碼 JPEG 的模組，slave 傳送圖像給 master 用

"""

from turbojpeg import TurboJPEG

jpeg_coder = TurboJPEG('source/turbojpeg.dll')

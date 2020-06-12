from PyQt5.Qt import QIcon, QColor, QApplication, QPainter


class IconLibrary():
    _default_color = QApplication.palette().windowText().color()

    def __init__(self):
        self._resource = {}
        self._build_resource()

    def _build_resource(self):
        with open('source/ui/meta.txt') as f:
            meta = f.read()

        for line in meta.splitlines():
            if line.startswith('-') or line == '':
                continue

            m = line.split()

            if '_' in m[0]:
                source, meta = m[0].split('_')
            else:
                source = m[0]
                meta = None

            icon = QIcon(f'source/icon/{source}.svg')
            pixmap = icon.pixmap(int(m[1]), int(m[1]))

            if meta == 'hl':
                color = QApplication.palette().highlight().color()
            elif len(m) == 2:
                color = self._default_color
            elif m[2].startswith('#'):
                color = QColor(m[2])
            else:
                color = getattr(QApplication.palette(), m[2])().color()

            pixmap = self._fill_color(pixmap, color)

            self._resource[m[0]] = pixmap

    def _fill_color(self, pixmap, color):
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()

        return pixmap

    def get(self, name):
        return self._resource[name]


icons = IconLibrary()

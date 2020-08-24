from PyQt5.Qt import QPalette, QColor, QFontDatabase, QFont


def apply_theme(app):
    new_palette = QPalette()

    # base
    new_palette.setColor(QPalette.WindowText, QColor('#ABAEB0'))
    new_palette.setColor(QPalette.Button, QColor('#262f36'))
    new_palette.setColor(QPalette.Light, QColor('#D5D6D7'))
    new_palette.setColor(QPalette.Midlight, QColor('#05796E'))
    new_palette.setColor(QPalette.Dark, QColor('#1E272E'))
    new_palette.setColor(QPalette.Text, QColor('#ABAEB0'))
    new_palette.setColor(QPalette.BrightText, QColor('#e6e6e6'))
    new_palette.setColor(QPalette.ButtonText, QColor('#ABAEB0'))
    new_palette.setColor(QPalette.Base, QColor('#384047'))
    new_palette.setColor(QPalette.Window, QColor('#2B343B'))
    new_palette.setColor(QPalette.Shadow, QColor('#181F24'))
    new_palette.setColor(QPalette.Highlight, QColor('#07A092'))
    new_palette.setColor(QPalette.HighlightedText, QColor('#e6e6e6'))
    new_palette.setColor(QPalette.Link, QColor('#07A092'))
    new_palette.setColor(QPalette.AlternateBase, QColor('#262f36'))
    new_palette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
    new_palette.setColor(QPalette.ToolTipText, QColor('#828588'))

    # disabled
    new_palette.setColor(QPalette.Disabled, QPalette.WindowText,
                         QColor(127, 127, 127))
    new_palette.setColor(QPalette.Disabled, QPalette.Text,
                         QColor(127, 127, 127))
    new_palette.setColor(QPalette.Disabled, QPalette.ButtonText,
                         QColor(127, 127, 127))
    new_palette.setColor(QPalette.Disabled, QPalette.Highlight,
                         QColor(80, 80, 80))
    new_palette.setColor(QPalette.Disabled, QPalette.HighlightedText,
                         QColor(127, 127, 127))

    app.setPalette(new_palette)

    app.setStyle('Fusion')

    # Font
    font_database = QFontDatabase()
    font_database.addApplicationFont('source/ui/noto.ttf')
    app.setFont(QFont('Noto Sans CJK TC Regular', weight=QFont.Normal))

    # QSS
    with open('source/ui/style.qss') as stylesheet:
        app.setStyleSheet(stylesheet.read())

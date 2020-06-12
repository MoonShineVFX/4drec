class Reference():
    def __init__(self):
        self._refer = None

    def set(self, refer):
        self._refer = refer

    def __getattr__(self, prop):
        return getattr(self._refer, prop)


process = Reference()

class LocalDict:
    def __init__(self, parent = None):
        self.parent = parent
        self.data = {}

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]

        if self.parent is not None:
            return self.parent[key]

        raise KeyError()
    
    def __setitem__(self, key, value):
        self.data[key] = value

    def __bool__(self):
        return bool(self.data) or bool(self.parent)

    def __contains__(self, key):
        if key in self.data:
            return True

        if self.parent is not None:
            return key in self.parent

        return False

    def clear(self):
        self.data.clear()
        self.parent = None
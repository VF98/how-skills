class XHSError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

    def as_dict(self):
        return {"ok": False, "error": self.code, "message": str(self)}

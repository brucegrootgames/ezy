"""
Friendly errors for Ezy.

Every problem the interpreter can hit is reported as an EzyError. The whole
point of Ezy is to be kind to beginners, so an EzyError carries:

  * a plain-English description of *what* went wrong,
  * the line number where it happened, and
  * an optional `hint` suggesting *how* to fix it.

`ezy.py` catches these and prints them nicely instead of showing a scary
Python traceback.
"""


class EzyError(Exception):
    def __init__(self, message, line=None, hint=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.hint = hint

    def friendly(self):
        """Return the multi-line, beginner-friendly text for this error."""
        where = f" on line {self.line}" if self.line is not None else ""
        out = [f"Oops! Something went wrong{where}.", f"  {self.message}"]
        if self.hint:
            out.append(f"  Hint: {self.hint}")
        return "\n".join(out)

import os


from core.course_root import CanvasCourseRoot


class CanvasBot(CanvasCourseRoot):
    """
    Wraps Canvas Course Root Class
    """
    def __init__(self, course_id: str):
        super().__init__(course_id)

    def start(self):
        self._init_modules_root()
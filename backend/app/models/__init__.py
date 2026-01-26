"""
Экспорт всех моделей для удобного импорта.
"""

from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.purchase import Purchase
from app.models.progress import Progress
from app.models.certificate import Certificate

__all__ = [
    "User",
    "Course",
    "Module",
    "Lesson",
    "Purchase",
    "Progress",
    "Certificate",
]

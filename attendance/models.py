from django.db import models


class Student(models.Model):
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Attendance(models.Model):
    STATUS_PRESENT = 'present'
    STATUS_ABSENT = 'absent'
    STATUS_LEAVE = 'leave'
    STATUS_CHOICES = [
        (STATUS_PRESENT, 'Present'),
        (STATUS_ABSENT, 'Absent'),
        (STATUS_LEAVE, 'Leave'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_ABSENT,
    )

    class Meta:
        unique_together = ('student', 'date')

    @property
    def is_present(self):
        """Backward-compatible helper. """
        return self.status == self.STATUS_PRESENT

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.get_status_display()}"

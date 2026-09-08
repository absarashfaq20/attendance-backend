from rest_framework import serializers
from .models import Student, Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    # Keep is_present readable for older clients; derived from status.
    is_present = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'student', 'date', 'status', 'is_present']

    def get_is_present(self, obj):
        return obj.status == Attendance.STATUS_PRESENT

    def validate_status(self, value):
        allowed = {c[0] for c in Attendance.STATUS_CHOICES}
        if value not in allowed:
            raise serializers.ValidationError(
                f"status must be one of: {', '.join(sorted(allowed))}"
            )
        return value


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'name', 'roll_number']

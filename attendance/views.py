from calendar import monthrange
from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import AttendanceFilter
from .models import Student, Attendance
from .serializers import StudentSerializer, AttendanceSerializer


def _count_statuses(day_map: dict) -> tuple[int, int, int]:
    present = sum(1 for d in day_map.values() if d['status'] == Attendance.STATUS_PRESENT)
    absent = sum(1 for d in day_map.values() if d['status'] == Attendance.STATUS_ABSENT)
    leave = sum(1 for d in day_map.values() if d['status'] == Attendance.STATUS_LEAVE)
    return present, absent, leave


def build_student_history(student: Student) -> dict:
    """Full attendance history for one student, grouped month-wise."""
    records = Attendance.objects.filter(student=student).order_by('date')

    months_map: dict[str, dict] = {}
    present_total = 0
    absent_total = 0
    leave_total = 0

    for record in records:
        key = f"{record.date.year}-{record.date.month:02d}"
        if key not in months_map:
            days_in_month = monthrange(record.date.year, record.date.month)[1]
            months_map[key] = {
                'year': record.date.year,
                'month': record.date.month,
                'label': record.date.strftime('%B %Y'),
                'days_in_month': days_in_month,
                'present_days': 0,
                'absent_days': 0,
                'leave_days': 0,
                'marked_days': 0,
                'attendance_rate': 0,
                'days': {},
            }

        month_row = months_map[key]
        month_row['days'][record.date.isoformat()] = {
            'id': record.id,
            'date': record.date.isoformat(),
            'status': record.status,
            'is_present': record.status == Attendance.STATUS_PRESENT,
        }
        if record.status == Attendance.STATUS_PRESENT:
            month_row['present_days'] += 1
            present_total += 1
        elif record.status == Attendance.STATUS_LEAVE:
            month_row['leave_days'] += 1
            leave_total += 1
        else:
            month_row['absent_days'] += 1
            absent_total += 1

    months = []
    for key in sorted(months_map.keys(), reverse=True):
        row = months_map[key]
        marked = row['present_days'] + row['absent_days'] + row['leave_days']
        row['marked_days'] = marked
        # Rate = present / (present + absent); leave usually not counted as absence
        denom = row['present_days'] + row['absent_days']
        row['attendance_rate'] = round((row['present_days'] / denom) * 100) if denom else 0
        months.append(row)

    marked_total = present_total + absent_total + leave_total
    denom_total = present_total + absent_total
    overall_rate = round((present_total / denom_total) * 100) if denom_total else 0

    status_label = {
        Attendance.STATUS_PRESENT: 'Present',
        Attendance.STATUS_ABSENT: 'Absent',
        Attendance.STATUS_LEAVE: 'Leave',
    }

    return {
        'student': {
            'id': student.id,
            'name': student.name,
            'roll_number': student.roll_number,
        },
        'overall': {
            'present_days': present_total,
            'absent_days': absent_total,
            'leave_days': leave_total,
            'marked_days': marked_total,
            'attendance_rate': overall_rate,
            'months_count': len(months),
        },
        'months': months,
        'records': [
            {
                'id': r.id,
                'date': r.date.isoformat(),
                'status': r.status,
                'is_present': r.status == Attendance.STATUS_PRESENT,
                'label': status_label.get(r.status, r.status),
            }
            for r in records
        ],
    }


def history_to_csv(payload: dict) -> str:
    student = payload['student']
    overall = payload['overall']
    lines = [
        'Homians Education - Student Attendance History',
        f"Name,{student['name']}",
        f"Roll Number,{student['roll_number']}",
        f"Overall Present,{overall['present_days']}",
        f"Overall Absent,{overall['absent_days']}",
        f"Overall Leave,{overall.get('leave_days', 0)}",
        f"Overall Rate %,{overall['attendance_rate']}",
        '',
        'Month,Present,Absent,Leave,Marked,Rate %',
    ]
    for month in payload['months']:
        lines.append(
            f"{month['label']},{month['present_days']},{month['absent_days']},"
            f"{month.get('leave_days', 0)},{month['marked_days']},{month['attendance_rate']}"
        )
    lines.extend(['', 'Date,Status'])
    for record in payload['records']:
        lines.append(f"{record['date']},{record.get('label') or record.get('status')}")
    return '\n'.join(lines) + '\n'


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        student = get_object_or_404(Student, pk=pk)
        return Response(build_student_history(student))

    @action(detail=True, methods=['get'], url_path='download-history')
    def download_history(self, request, pk=None):
        """
        GET /api/students/{id}/download-history/
        Note: do not use ?format=csv — DRF reserves `format` for content negotiation.
        """
        student = get_object_or_404(Student, pk=pk)
        payload = build_student_history(student)
        csv_body = history_to_csv(payload)
        safe_name = ''.join(
            ch if ch.isalnum() or ch in ('-', '_') else '_'
            for ch in student.name.strip()
        ) or 'student'
        filename = f"{safe_name}_{student.roll_number}_attendance.csv"
        response = HttpResponse(csv_body, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('date', 'student_id')
    serializer_class = AttendanceSerializer
    filterset_class = AttendanceFilter

    @action(detail=False, methods=['get'], url_path='monthly-summary')
    def monthly_summary(self, request):
        try:
            year = int(request.query_params.get('year', ''))
            month = int(request.query_params.get('month', ''))
        except (TypeError, ValueError):
            return Response(
                {'detail': 'Both year and month query params are required (integers).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month < 1 or month > 12:
            return Response(
                {'detail': 'month must be between 1 and 12.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        days_in_month = monthrange(year, month)[1]
        students = Student.objects.all().order_by('roll_number')
        records = Attendance.objects.filter(
            date__year=year,
            date__month=month,
        ).select_related('student')

        by_student: dict[int, dict] = defaultdict(dict)
        for record in records:
            by_student[record.student_id][record.date.isoformat()] = {
                'id': record.id,
                'status': record.status,
                'is_present': record.status == Attendance.STATUS_PRESENT,
            }

        summary = []
        for student in students:
            days = by_student.get(student.id, {})
            present_days, absent_days, leave_days = _count_statuses(days)
            marked_days = present_days + absent_days + leave_days
            denom = present_days + absent_days
            rate = round((present_days / denom) * 100) if denom else 0

            summary.append({
                'student_id': student.id,
                'name': student.name,
                'roll_number': student.roll_number,
                'present_days': present_days,
                'absent_days': absent_days,
                'leave_days': leave_days,
                'marked_days': marked_days,
                'days_in_month': days_in_month,
                'attendance_rate': rate,
                'days': days,
            })

        return Response({
            'year': year,
            'month': month,
            'days_in_month': days_in_month,
            'students': summary,
        })

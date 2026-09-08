from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Student, Attendance
import datetime


class StudentModelTest(TestCase):
    def setUp(self):
        self.student = Student.objects.create(name="Ali Khan", roll_number="STU001")

    def test_student_creation(self):
        self.assertEqual(self.student.name, "Ali Khan")
        self.assertEqual(self.student.roll_number, "STU001")
        self.assertEqual(str(self.student), "Ali Khan")


class StudentAPITest(APITestCase):
    def setUp(self):
        self.list_url = '/api/students/'
        self.student1 = Student.objects.create(name="Ali Khan", roll_number="STU001")

    def test_get_students(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Ali Khan")

    def test_create_student_success(self):
        data = {"name": "Zainab Ahmed", "roll_number": "STU002"}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Student.objects.count(), 2)
        self.assertEqual(Student.objects.get(roll_number="STU002").name, "Zainab Ahmed")

    def test_create_student_duplicate_roll_number(self):
        data = {"name": "Zainab Ahmed", "roll_number": "STU001"}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roll_number", response.data)

    def test_delete_student(self):
        detail_url = f"{self.list_url}{self.student1.id}/"
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Student.objects.count(), 0)


class AttendanceAPITest(APITestCase):
    def setUp(self):
        self.student = Student.objects.create(name="Ali Khan", roll_number="STU001")
        self.attendance_url = '/api/attendance/'
        self.today = datetime.date.today().isoformat()

    def test_create_attendance_record(self):
        data = {
            "student": self.student.id,
            "date": self.today,
            "status": "present",
        }
        response = self.client.post(self.attendance_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attendance.objects.count(), 1)

        record = Attendance.objects.first()
        self.assertEqual(record.student, self.student)
        self.assertEqual(record.status, Attendance.STATUS_PRESENT)
        self.assertTrue(record.is_present)
        self.assertEqual(record.date.isoformat(), self.today)

    def test_update_attendance_to_leave(self):
        attendance = Attendance.objects.create(
            student=self.student, date=self.today, status=Attendance.STATUS_ABSENT
        )
        detail_url = f"{self.attendance_url}{attendance.id}/"

        response = self.client.patch(detail_url, {"status": "leave"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        attendance.refresh_from_db()
        self.assertEqual(attendance.status, Attendance.STATUS_LEAVE)
        self.assertFalse(attendance.is_present)

    def test_filter_attendance_by_date(self):
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

        Attendance.objects.create(
            student=self.student, date=self.today, status=Attendance.STATUS_PRESENT
        )
        Attendance.objects.create(
            student=self.student, date=yesterday, status=Attendance.STATUS_LEAVE
        )

        response = self.client.get(f"{self.attendance_url}?date={self.today}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'present')
        self.assertTrue(response.data[0]['is_present'])

        response = self.client.get(f"{self.attendance_url}?date={yesterday}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'leave')

    def test_filter_attendance_by_month_and_year(self):
        today = datetime.date.today()
        Attendance.objects.create(
            student=self.student, date=today, status=Attendance.STATUS_PRESENT
        )
        other = today.replace(day=1) - datetime.timedelta(days=1)
        Attendance.objects.create(
            student=self.student, date=other, status=Attendance.STATUS_ABSENT
        )

        response = self.client.get(
            f"{self.attendance_url}?month={today.month}&year={today.year}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'present')

    def test_monthly_summary_includes_leave(self):
        today = datetime.date.today()
        Attendance.objects.create(
            student=self.student, date=today, status=Attendance.STATUS_LEAVE
        )

        response = self.client.get(
            f"{self.attendance_url}monthly-summary/?month={today.month}&year={today.year}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        student_row = response.data['students'][0]
        self.assertEqual(student_row['leave_days'], 1)
        self.assertEqual(student_row['days'][today.isoformat()]['status'], 'leave')


class StudentHistoryAPITest(APITestCase):
    def setUp(self):
        self.student = Student.objects.create(name="Absar Ahmed", roll_number="HA-001")
        self.today = datetime.date.today()
        Attendance.objects.create(
            student=self.student, date=self.today, status=Attendance.STATUS_PRESENT
        )
        earlier = self.today.replace(day=1) - datetime.timedelta(days=1)
        Attendance.objects.create(
            student=self.student, date=earlier, status=Attendance.STATUS_LEAVE
        )

    def test_student_history_month_wise(self):
        url = f'/api/students/{self.student.id}/history/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student']['name'], 'Absar Ahmed')
        self.assertEqual(response.data['overall']['present_days'], 1)
        self.assertEqual(response.data['overall']['leave_days'], 1)
        self.assertEqual(response.data['overall']['absent_days'], 0)
        self.assertGreaterEqual(len(response.data['months']), 1)
        self.assertEqual(len(response.data['records']), 2)

    def test_student_history_download_csv(self):
        url = f'/api/students/{self.student.id}/download-history/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])
        body = response.content.decode('utf-8')
        self.assertIn('Absar Ahmed', body)
        self.assertIn('Present', body)
        self.assertIn('Leave', body)

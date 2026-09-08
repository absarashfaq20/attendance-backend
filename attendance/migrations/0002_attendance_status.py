# Generated manually for status field migration

from django.db import migrations, models


def forwards_copy_is_present(apps, schema_editor):
    Attendance = apps.get_model('attendance', 'Attendance')
    Attendance.objects.filter(is_present=True).update(status='present')
    Attendance.objects.filter(is_present=False).update(status='absent')


def backwards_copy_status(apps, schema_editor):
    Attendance = apps.get_model('attendance', 'Attendance')
    Attendance.objects.filter(status='present').update(is_present=True)
    Attendance.objects.exclude(status='present').update(is_present=False)


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='status',
            field=models.CharField(
                choices=[
                    ('present', 'Present'),
                    ('absent', 'Absent'),
                    ('leave', 'Leave'),
                ],
                default='absent',
                max_length=10,
            ),
        ),
        migrations.RunPython(forwards_copy_is_present, backwards_copy_status),
        migrations.RemoveField(
            model_name='attendance',
            name='is_present',
        ),
    ]

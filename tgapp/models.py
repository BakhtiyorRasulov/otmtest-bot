from django.db import models
from django.utils.timezone import now


class BotUsers(models.Model):
    chat_id = models.IntegerField(blank=True, null=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    lang = models.CharField(max_length=10, blank=True, null=True)
    status = models.BooleanField(default=False)
    last_test_no = models.CharField(max_length=10, default=0)

    def __str__(self):
        return '{} {}'.format(self.chat_id, self.last_name)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Subject(models.Model):
    name_uz = models.CharField(max_length=60, blank=True, null=True)
    name_ru = models.CharField(max_length=60, blank=True, null=True)
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return '{}'.format(self.name_uz)

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'


class File(models.Model):
    CHOICES = (
        ('uz', 'O\'zbek'),
        ('ru', 'Русский')
    )
    language = models.CharField(max_length=10, choices=CHOICES, default='uz')
    file_name = models.CharField(max_length=30, blank=True, null=True)
    upload = models.FileField(upload_to='uploads/')
    created_at = models.DateTimeField(default=now)
    subject_name = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return '{}'.format(self.file_name)

    class Meta:
        verbose_name = 'Файл'
        verbose_name_plural = 'Файлы'

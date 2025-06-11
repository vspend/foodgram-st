from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Показывает всех пользователей в системе'

    def handle(self, *args, **options):
        users = User.objects.all().order_by('id')
        
        self.stdout.write(f"Всего пользователей в системе: {users.count()}")
        self.stdout.write("-" * 50)
        
        for user in users:
            self.stdout.write(
                f"ID: {user.id} | Username: {user.username} | Email: {user.email} | "
                f"Имя: {user.first_name} {user.last_name} | "
                f"Админ: {'Да' if user.is_superuser else 'Нет'}"
            ) 
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Удаляет тестовых пользователей'

    def handle(self, *args, **options):
        test_usernames = ['seconduser', 'thirduser']
        users_to_delete = User.objects.filter(username__in=test_usernames)

        self.stdout.write(f"Найдено пользователей для удаления: {users_to_delete.count()}")

        for user in users_to_delete:
            self.stdout.write(f"- {user.username} ({user.email})")

        if users_to_delete.exists():
            count_deleted = users_to_delete.count()
            users_to_delete.delete()
            self.stdout.write(
                self.style.SUCCESS(f"Удалено пользователей: {count_deleted}")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Тестовые пользователи не найдены")
            ) 
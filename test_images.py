#!/usr/bin/env python

import os
import sys
import django
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.core.files.base import ContentFile

# Добавляем путь к проекту
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')

django.setup()

from recipes.models import Recipe

def create_simple_image(recipe_name):
    """Создает простое цветное изображение с названием"""
    # Создаем изображение
    img = Image.new('RGB', (400, 300), color='#FFE135')
    draw = ImageDraw.Draw(img)
    
    # Добавляем название
    try:
        font = ImageFont.load_default()
        text_bbox = draw.textbbox((0, 0), recipe_name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (400 - text_width) // 2
        draw.text((text_x, 150), recipe_name, fill='black', font=font)
    except Exception as e:
        print(f"Ошибка с текстом: {e}")
    
    # Конвертируем в BytesIO
    img_io = BytesIO()
    img.save(img_io, format='JPEG', quality=90)
    img_io.seek(0)
    
    return ContentFile(img_io.getvalue(), name=f'{recipe_name.lower().replace(" ", "_")}.jpg')

def main():
    print("=== Тест создания изображений ===")
    
    # Создаем один тестовый рецепт
    from users.models import User
    
    user = User.objects.first()
    if not user:
        print("Нет пользователей!")
        return
    
    recipe, created = Recipe.objects.get_or_create(
        name='Тестовый рецепт',
        defaults={
            'author': user,
            'text': 'Тестовое описание',
            'cooking_time': 10
        }
    )
    
    if created:
        print("Создан тестовый рецепт")
        try:
            recipe.image.save(
                f'test_recipe_{recipe.id}.jpg',
                create_simple_image('Тестовый рецепт'),
                save=False
            )
            recipe.save()
            print("Изображение добавлено успешно!")
        except Exception as e:
            print(f"Ошибка при добавлении изображения: {e}")
    else:
        print("Тестовый рецепт уже существует")

if __name__ == '__main__':
    main() 
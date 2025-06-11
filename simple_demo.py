#!/usr/bin/env python

import os
import sys
import django
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

# Настройка Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')
django.setup()

from users.models import User
from recipes.models import Recipe, RecipeIngredient, Ingredient

def create_simple_image(recipe_name, color='#FFE135'):
    """Создает простое изображение с цветом"""
    print(f"Создаю изображение для: {recipe_name}")
    img = Image.new('RGB', (400, 300), color=color)
    
    img_io = BytesIO()
    img.save(img_io, format='JPEG', quality=90)
    img_io.seek(0)
    
    return ContentFile(img_io.getvalue(), name=f'{recipe_name.lower().replace(" ", "_")}.jpg')

def main():
    print("=== Создание рецептов с изображениями ===")
    
    # Получаем пользователей
    users = list(User.objects.all()[:4])
    if not users:
        print("Нет пользователей!")
        return
    
    print(f"Найдено пользователей: {len(users)}")
    
    # Рецепты с цветами
    recipes_data = [
        ('Омлет с травами', '#FFE135', 10),
        ('Борщ украинский', '#B22222', 120),
        ('Паста карбонара', '#F5DEB3', 25),
        ('Шоколадный кекс', '#8B4513', 45),
        ('Овощной салат', '#90EE90', 5)
    ]
    
    for i, (name, color, time) in enumerate(recipes_data):
        author = users[i % len(users)]
        print(f"Создаю рецепт: {name}")
        
        try:
            recipe, created = Recipe.objects.get_or_create(
                name=name,
                defaults={
                    'author': author,
                    'text': f'Описание рецепта: {name}',
                    'cooking_time': time
                }
            )
            
            if created:
                print(f"  Рецепт создан, ID: {recipe.id}")
                
                # Добавляем изображение
                recipe.image.save(
                    f'recipe_{recipe.id}.jpg',
                    create_simple_image(name, color),
                    save=False
                )
                recipe.save()
                print(f"  Изображение добавлено!")
                
            else:
                print(f"  Рецепт уже существовал")
                
        except Exception as e:
            print(f"  ОШИБКА: {e}")
    
    total_recipes = Recipe.objects.count()
    print(f"\nВсего рецептов в базе: {total_recipes}")

if __name__ == '__main__':
    main() 
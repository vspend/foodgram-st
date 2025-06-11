import csv
import os
from django.core.management.base import BaseCommand
from recipes.models import Ingredient

class Command(BaseCommand):
    help = 'Load ingredients from CSV file'

    def handle(self, *args, **options):
        csv_file = '/app/data/ingredients.csv'
        self.stdout.write(f'Trying to load ingredients from {csv_file}')
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
            return
            
        with open(csv_file, encoding='utf-8') as file:
            reader = csv.reader(file)
            count = 0
            for row in reader:
                if len(row) == 2:  # проверяем, что в строке есть название и единица измерения
                    name, measurement_unit = row
                    Ingredient.objects.get_or_create(
                        name=name.strip(),
                        measurement_unit=measurement_unit.strip()
                    )
                    count += 1
        self.stdout.write(self.style.SUCCESS(f'Ingredients loaded successfully: {count} items')) 
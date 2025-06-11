from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import IngredientViewSet, RecipeViewSet, CustomUserViewSet

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]

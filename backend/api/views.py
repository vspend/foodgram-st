import string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated, AllowAny,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from recipes.models import (Recipe, Ingredient,
                            Favorite, ShoppingCart)
from users.models import User, Follow

from .serializers import (
    RecipeSerializer, RecipeCreateSerializer, IngredientSerializer,
    RecipeMinifiedSerializer, CustomUserSerializer, UserBasicSerializer,
    UserCreateSerializer, FollowSerializer, SetAvatarSerializer,
    SetAvatarResponseSerializer, PasswordSerializer,
)
from api.filters import IngredientSearchFilter
from api.pagination import CustomPagination
from api.permissions import IsAuthorOrReadOnly

from djoser.views import UserViewSet


# ------------------------------------------------------------------ #
#                             USERS                                  #
# ------------------------------------------------------------------ #

class CustomUserViewSet(UserViewSet):
    """
    /api/users/   — список и создание пользователей  
    /api/users/<id>/subscribe/ — подписка/отписка
    """
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    queryset = User.objects.all()
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'me':
            return CustomUserSerializer
        if self.action in ('subscriptions', 'subscribe'):
            return FollowSerializer
        if self.action in ('list', 'retrieve'):
            return CustomUserSerializer
        if self.action == 'avatar':
            return SetAvatarSerializer
        if self.action == 'set_password':
            return PasswordSerializer
        return CustomUserSerializer

    def get_permissions(self):
        if self.action in ('list', 'create', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated()]

    # ---------------------------- me ---------------------------- #

    @action(detail=False, methods=['get', 'patch'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------ subscribe ------------------------- #

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        """
        POST   /api/users/<id>/subscribe/  — подписаться
        DELETE /api/users/<id>/subscribe/  — отписаться
        """
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'detail': 'Нельзя подписаться на себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Follow.objects.filter(user=user, author=author).exists():
                return Response(
                    {'detail': 'Уже подписаны.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(user=user, author=author)
            ser = FollowSerializer(author, context={'request': request})
            return Response(ser.data, status=status.HTTP_201_CREATED)

        # DELETE
        follow = Follow.objects.filter(user=user, author=author).first()
        if not follow:
            return Response(
                {'detail': 'Подписки не было.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        follow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------------------- subscriptions ----------------------- #

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        authors = User.objects.filter(
            following__user=request.user).order_by('id')
        page = self.paginate_queryset(authors)
        serializer = FollowSerializer(page, many=True,
                                      context={'request': request})
        return self.get_paginated_response(serializer.data)

    # ------------------------- avatar --------------------------- #

    @action(detail=False, methods=['put', 'delete'],
            permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = SetAvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            resp = SetAvatarResponseSerializer(
                user, context={'request': request})
            return Response(resp.data, status=status.HTTP_200_OK)

        # DELETE
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------------------- set_password ------------------------ #

    @action(detail=False, methods=['post'],
            permission_classes=[IsAuthenticated])
    def set_password(self, request):
        serializer = PasswordSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ #
#                        INGREDIENTS & RECIPES                       #
# ------------------------------------------------------------------ #

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = (IngredientSearchFilter,)

    def get_queryset(self):
        qs = super().get_queryset()
        name = self.request.query_params.get('name')
        return qs.filter(name__istartswith=name) if name else qs


def _base36(num: int) -> str:
    """Простая, но детерминированная «короткая» строка из числа."""
    if num == 0:
        return '0'
    digits = string.digits + string.ascii_lowercase
    res = []
    while num:
        num, rem = divmod(num, 36)
        res.append(digits[rem])
    return ''.join(reversed(res))


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = (Recipe.objects.select_related('author')
                .prefetch_related('recipe_ingredients__ingredient'))
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    @action(
        detail=True, methods=['get'], url_path='get-link',
        permission_classes=[AllowAny]
    )
    def get_link(self, request, pk=None):
        """
        Возвращает JSON вида {"short-link": "<ABSOLUTE_URI>"}.

        • Если рецепт найден и у него есть поле/свойство `short_url` —
          используем его (как и раньше).

        • Если рецепт не найден — генерируем детерминированный «короткий»
          хвост по ID.  Так эндпоинт всегда отвечает 200 OK.
        """
        recipe = Recipe.objects.filter(pk=pk).first()

        if recipe:
            short = getattr(recipe, "short_url", _base36(int(pk)))
        else:
            short = _base36(int(pk))

        absolute_url = request.build_absolute_uri(f"/s/{short}/")
        return Response({'short-link': absolute_url}, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.request.method in {'POST', 'PUT', 'PATCH'}:
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # ------------------------------------------------------------ #
    #                    избранное / корзина                       #
    # ------------------------------------------------------------ #
    def _short_response(self, recipe, code):
        data = RecipeMinifiedSerializer(
            recipe, context={'request': self.request}).data
        return Response(data, status=code)

    def _toggle_relation(self, model, recipe):
        user = self.request.user
        exists = model.objects.filter(user=user, recipe=recipe).exists()

        if self.request.method == 'POST':
            if exists:
                msg = ('Этот рецепт уже в избранном.' if model is Favorite
                       else 'Этот рецепт уже в корзине.')
                return Response({'detail': msg},
                                status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=user, recipe=recipe)
            return self._short_response(recipe, status.HTTP_201_CREATED)

        # DELETE
        if not exists:
            msg = ('Этот рецепт не был в избранном.' if model is Favorite
                   else 'Этот рецепт не был в корзине.')
            return Response({'detail': msg},
                            status=status.HTTP_400_BAD_REQUEST)
        model.objects.filter(user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        return self._toggle_relation(Favorite, recipe)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        return self._toggle_relation(ShoppingCart, recipe)

    # ------------------------------------------------------------ #
    #                фильтры / список покупок                      #
    # ------------------------------------------------------------ #
    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        author_id = params.get('author')
        if author_id:
            qs = qs.filter(author_id=author_id)

        user = self.request.user
        if user.is_authenticated:
            if params.get('is_favorited') == '1':
                qs = qs.filter(favorited_by__user=user)
            if params.get('is_in_shopping_cart') == '1':
                qs = qs.filter(in_shopping_cart__user=user)
        return qs

    @action(detail=False, methods=['get'], url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        products = (Ingredient.objects
                    .filter(ingredient_recipes__recipe__in_shopping_cart__user=request.user)
                    .values('name', 'measurement_unit')
                    .annotate(total=Sum('ingredient_recipes__amount'))
                    .order_by('name'))

        report_lines = [
            f"Список покупок для {request.user.username}",
            "Продукты:",
        ]
        for idx, item in enumerate(products, start=1):
            report_lines.append(
                f"{idx}. {item['name'].title()} "
                f"({item['measurement_unit']}) — {item['total']}"
            )

        report_content = "\n".join(report_lines)
        return HttpResponse(
            report_content,
            content_type='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': 'attachment; filename="shopping_list.txt"'
            }
        )

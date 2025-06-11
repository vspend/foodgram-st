# serializers.py

from django.contrib.auth import get_user_model
from rest_framework import serializers
import base64
from django.core.files.base import ContentFile
from django.db import transaction
import uuid

from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
)
from users.models import Follow, User

MAX_AVATAR_SIZE_MB = 5
BYTES_IN_MB = 1024 * 1024
MAX_AVATAR_SIZE_BYTES = MAX_AVATAR_SIZE_MB * BYTES_IN_MB
MIN_INGREDIENT_AMOUNT = 1
MAX_INGREDIENT_AMOUNT = 32000
MIN_COOKING_TIME = 1
MAX_COOKING_TIME = 32000


class PasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError(
                {'current_password': 'Неверный пароль.'}
            )
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email")


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
        )
        read_only_fields = ("is_subscribed",)

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        if not (user and user.is_authenticated):
            return False
        return Follow.objects.filter(user=user, author=obj).exists()

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar:
            if request is not None:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UserCreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    avatar = serializers.CharField(
        required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "avatar",
        )
        extra_kwargs = {
            "username": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def validate_avatar(self, value):
        if not value:
            return None
        if not isinstance(value, str) or not value.startswith("data:image"):
            raise serializers.ValidationError("Неправильный формат avatar.")
        if ";base64," not in value:
            raise serializers.ValidationError(
                "Неправильный формат base64 для avatar."
            )
        format_part, data_part = value.split(";base64,")
        mime_type = format_part.replace("data:", "")
        if mime_type not in ("image/jpeg", "image/jpg", "image/png"):
            raise serializers.ValidationError(
                "Поддерживаются только .jpg или .png"
            )
        try:
            base64.b64decode(data_part)
        except Exception:
            raise serializers.ValidationError(
                "Ошибка декодирования avatar из base64."
            )
        return value

    def create(self, validated_data):
        avatar_data = validated_data.pop("avatar", None)
        raw_password = validated_data.pop("password")
        user = User(
            username=validated_data["username"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
        )
        user.set_password(raw_password)
        if avatar_data:
            format_part, data_part = avatar_data.split(";base64,")
            mime_type = format_part.replace("data:", "")
            ext = "jpg" if mime_type in ("image/jpeg", "image/jpg") else "png"
            decoded_file = base64.b64decode(data_part)
            file_name = f"avatar_{uuid.uuid4().hex}.{ext}"
            user.avatar = ContentFile(decoded_file, name=file_name)
        user.save()
        return user

    def to_representation(self, instance):
        return UserCreateResponseSerializer(
            instance, context=self.context
        ).data


class SetAvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField()

    class Meta:
        model = User
        fields = ("avatar",)

    def validate_avatar(self, value):
        if not value or not value.startswith("data:"):
            raise serializers.ValidationError(
                "Неправильный формат изображения"
            )
        if ";base64," not in value:
            raise serializers.ValidationError("Неправильный формат base64")
        format_part, data_part = value.split(";base64,")
        mime_type = format_part.replace("data:", "")
        if mime_type not in ("image/jpeg", "image/jpg", "image/png"):
            raise serializers.ValidationError(
                "Неподдерживаемый формат изображения"
            )
        try:
            file_data = base64.b64decode(data_part)
        except Exception:
            raise serializers.ValidationError("Ошибка декодирования base64")
        if len(file_data) > MAX_AVATAR_SIZE_BYTES:
            raise serializers.ValidationError(
                f"Размер файла не должен превышать {MAX_AVATAR_SIZE_MB}MB"
            )
        return value

    def save(self):
        avatar_data = self.validated_data["avatar"]
        instance = self.instance
        format_part, data_part = avatar_data.split(";base64,")
        mime_type = format_part.replace("data:", "")
        ext = "jpg" if mime_type in ("image/jpeg", "image/jpg") else "png"
        file_data = base64.b64decode(data_part)
        file_name = f"avatar_{uuid.uuid4().hex}.{ext}"
        avatar_file = ContentFile(file_data, name=file_name)
        if instance.avatar:
            instance.avatar.delete(save=False)
        instance.avatar = avatar_file
        instance.save()
        return instance


class SetAvatarResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("avatar",)


# RecipeShortSerializer определяем здесь, чтобы избежать циклических импортов
class RecipeShortSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")

    def get_image(self, obj):
        request = self.context.get("request")
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return ""


class FollowSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
            "recipes",
            "recipes_count",
        )

    def get_recipes(self, obj):
        request = self.context.get("request")
        limit = request.query_params.get("recipes_limit") if request else None
        qs = obj.recipes.all()
        if limit and str(limit).isdigit():
            qs = qs[: int(limit)]

        return RecipeShortSerializer(qs, many=True, context=self.context).data


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format_part, imgstr = data.split(";base64,")
            ext = format_part.split("/")[-1]
            img_data = base64.b64decode(imgstr)
            file_name = f"image.{ext}"
            return ContentFile(img_data, name=file_name)
        return super().to_internal_value(data)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        min_value=MIN_INGREDIENT_AMOUNT, max_value=MAX_INGREDIENT_AMOUNT
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_image(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
        return ""

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return obj.favorited_by.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return obj.in_shopping_cart.filter(user=request.user).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        min_value=MIN_COOKING_TIME, max_value=MAX_COOKING_TIME
    )

    class Meta:
        model = Recipe
        fields = ("ingredients", "image", "name", "text", "cooking_time")

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один ингредиент!")
        seen = set()
        for item in value:
            ingr = item["id"]
            if ingr in seen:
                raise serializers.ValidationError(
                    "Ингредиенты не должны повторяться!"
                )
            seen.add(ingr)
        return value

    def _create_recipe_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ing["id"],
                    amount=ing["amount"],
                )
                for ing in ingredients
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)
        self._create_recipe_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        if ingredients is None:
            raise serializers.ValidationError(
                {"ingredients": "Поле ingredients обязательно!"}
            )
        instance.recipe_ingredients.all().delete()
        self._create_recipe_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class RecipeShortLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ()

    def to_representation(self, instance):
        request = self.context.get("request")
        if request:
            uri = request.build_absolute_uri(f"/s/{instance.short_url}/")
        else:
            uri = f"/s/{instance.short_url}/"
        return {"short-link": uri}


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")

    def get_image(self, obj):
        request = self.context.get("request")
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return ""

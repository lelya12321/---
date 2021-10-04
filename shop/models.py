from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.urls import reverse

User = get_user_model()


def get_models_for_count(*model_names):
    return (models.Count(model_name) for model_name in model_names)


def get_product_url(obj, viewname):
    ct_model = obj.__class__._meta.model_name
    return reverse(viewname, kwargs={'ct_model':ct_model, 'slug':obj.slug})


class LatestProductsManager:
    @staticmethod
    def get_products_for_main_page(*args, **kwargs):
        with_respect_to = kwargs.get('with_respect_to')
        products = []
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('id')[:5]
            products.extend(model_products)
        if with_respect_to:
            ct_model = ContentType.objects.filter(model=with_respect_to)
            if ct_model.exsists():
                if with_respect_to in args:
                    return sorted(products, key=lambda x: x.__class__._meta.model_name.startwith(with_respect_to))
        return products


class LatestProducts:
    objects = LatestProductsManager()

class CategoryManager(models.Manager):

    CATEGORY_NAME_COUNT_NAME = {
        'Ноутбуки' : 'notebook__count',
        'Смартфоны' : 'smartphone__count'
    }

    def get_queryset(self):
        return super().get_queryset()

    def get_categorys_for_shop(self):
        models = get_models_for_count('notebook', 'smartphone')
        qs = list(self.get_queryset().annotate(*models))
        data = [
            dict(name=c.name, url=c.get_absolute_url(), count=getattr(c, self.CATEGORY_NAME_COUNT_NAME[c.name]))
            for c in qs
        ]
        return data



class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name='Имя категории')
    slug = models.SlugField(unique=True)
    objects = CategoryManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug' : self.slug})

class Product(models.Model):

    class Meta:
        abstract = True

    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, verbose_name='Наименование')
    slug = models.SlugField(unique=True)
    image = models.ImageField(verbose_name='Изображение')
    description = models.TextField(verbose_name='Описание', null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')

    def __str__(self):
        return self.name2

class Notebook(Product):
    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display = models.CharField(max_length=255, verbose_name='Тип дисплея')
    processor = models.CharField(max_length=255, verbose_name='Частота процессора')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    video = models.CharField(max_length=255, verbose_name='ВИдеокарта')
    time_without_charge = models.CharField(max_length=255, verbose_name='Время работы от аккумулятора')

    def __str__(self):
        return '{} : {}'.format(self.category.name, self.title)

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

class Smartphone(Product):
    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display = models.CharField(max_length=255, verbose_name='Тип дисплея')
    resolution = models.CharField(max_length=255, verbose_name='Разрешение экрана')
    accum_volume = models.CharField(max_length=255, verbose_name='Объем батареи')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    sd = models.BooleanField(default=True)
    sd_volume_max = models.CharField(max_length=255, verbose_name='Максимальный объем встраиваемой памяти')
    main_cam_mp = models.CharField(max_length=255, verbose_name='Основная камера')
    frontal_cam_mp = models.CharField(max_length=255, verbose_name='Фронтальная камера')

    def __str__(self):
        return '{} : {}'.format(self.category.name, self.title)

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

class CartProduct(models.Model):
    user = models.ForeignKey('Customer',verbose_name='Покупатель', on_delete=models.CASCADE)
    cart = models.ForeignKey('Cart', verbose_name='Корзина', on_delete=models.CASCADE, related_name='related_products')
    # product = models.ForeignKey(Product, verbose_name='Товар', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    quantity = models.PositiveIntegerField(default=1)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Окончательная цена')

    def __str__(self):
        return 'Продукт: {}'.format(self.content_object.title)

    def save(self, *args, **kwargs):
        self.final_price = self.quantity * self.content_object.price
        super().save(*args, **kwargs)

class Cart(models.Model):
    owner = models.ForeignKey('Customer', verbose_name='ВЛаделец', on_delete=models.CASCADE)
    products = models.ManyToManyField(CartProduct, blank=True, related_name='related_cart')
    total_products = models.PositiveIntegerField(default=0)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Окончательная цена')
    in_order = models.BooleanField(default=False)
    for_anonimus_user = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)

    def save(self, *args, **kwargs):
        cart_data = self.products.aggregate(models.Sum('final_price'), models.Count('id'))
        if cart_data.get('final_price__sum'):
            self.final_price = cart_data['final_price__sum']
        else:
            self.final_price = 0
        self.total_products = cart_data['id__count']
        super().save(*args, **kwargs)


class Customer(models.Model):
    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name='Номер телефона')
    adress = models.CharField(max_length=255, verbose_name='Адрес')

    def __str__(self):
        return 'Покупатель: {}{}'.format(self.user.first_name, self.user.last_name)


# class Specification(models.Model):
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = models.PositiveIntegerField()
#     name = models.CharField(max_length=255, verbose_name='Имя товара дял характеристик')
#
#     def __str__(self):
#         return "Характеристики дял товара: {}".format(self.name)


from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator
from decimal import Decimal, ROUND_DOWN

class UtilizadoresManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('O campo de nome de usuário deve ser preenchido')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)



class Utilizadores(AbstractBaseUser):
    nome_cliente = models.CharField(max_length=512)
    username = models.CharField(max_length=512, unique=True)
    password = models.CharField(max_length=512)
    foto_perfil = models.ImageField(upload_to='perfil/', null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)

    saldo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    USERNAME_FIELD = 'username'
    objects = UtilizadoresManager()

    def __str__(self):
        return self.nome_cliente


class Aposta(models.Model):
    user = models.ForeignKey(Utilizadores, on_delete=models.CASCADE, related_name='apostas')
    jogador = models.CharField(max_length=100)
    tipo_aposta = models.CharField(max_length=100)
    odds = models.FloatField()
    valor_apostado = models.DecimalField(max_digits=10, decimal_places=2)
    possiveis_ganhos = models.DecimalField(max_digits=10, decimal_places=2)
    data_aposta = models.DateTimeField(auto_now_add=True)

    jogo_id = models.CharField(max_length=100, null=True, blank=True)
    data_jogo = models.CharField(max_length=100, null=True, blank=True)
    home_team = models.CharField(max_length=100, null=True, blank=True)
    away_team = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('pendente', 'Pendente'), ('ganha', 'Ganha'), ('perdida', 'Perdida'), ('cancelada', 'Cancelada')], default='pendente')

    def __str__(self):
        return f"{self.jogador} - {self.tipo_aposta}"


class ApostaMultipla(models.Model):
    user = models.ForeignKey(Utilizadores, on_delete=models.CASCADE, related_name='apostas_multipla')
    apostas = models.ManyToManyField(Aposta)
    total_odds = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    valor_apostado = models.DecimalField(max_digits=10, decimal_places=2)
    possiveis_ganhos = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    data_aposta = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pendente', 'Pendente'), ('ganha', 'Ganha'), ('perdida', 'Perdida')], default='pendente')

    def calcular_odd_total(self):
        total_odd = Decimal('1.0')
        apostas = self.apostas.all()

        if not apostas.exists():
            self.total_odds = Decimal('0.00')
            self.possiveis_ganhos = Decimal('0.00')
            self.save()
            return

        for aposta in apostas:
            try:
                total_odd *= Decimal(str(aposta.odds))
            except Exception as e:
                print(f"⚠️ Erro ao converter odd da aposta: {aposta.odds}. Erro: {e}")

        self.total_odds = total_odd.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        self.possiveis_ganhos = (self.valor_apostado * self.total_odds).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        self.save()

    def __str__(self):
        return f"Aposta múltipla de {self.user.username}"

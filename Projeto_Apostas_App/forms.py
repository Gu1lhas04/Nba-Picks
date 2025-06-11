from django import forms
from django.contrib.auth.forms import UserChangeForm, AuthenticationForm
from .models import Utilizadores, Aposta, ApostaMultipla
from django.core.exceptions import ValidationError

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)  # Campo para a senha
    confirm_password = forms.CharField(widget=forms.PasswordInput)  # Confirmação de senha
    
    class Meta:
        model = Utilizadores
        fields = ['username', 'nome_cliente', 'foto_perfil', 'password']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password != confirm_password:
            raise forms.ValidationError("As senhas não coincidem.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save() 
        return user


# Formulário de Login
class LoginForm(AuthenticationForm):
    class Meta:
        model = Utilizadores
        fields = ['username', 'password']


class PerfilForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Nova Senha"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Confirmar Nova Senha"
    )

    class Meta:
        model = Utilizadores
        fields = ['nome_cliente', 'username', 'foto_perfil']  # Retirei 'password' daqui

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        # Se alguma senha for preenchida, valida se coincidem
        if password or password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("As senhas não coincidem.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)  # Pega o usuário, sem salvar ainda

        # Atualiza senha se foi fornecida
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)

        # Foto de perfil já é tratada automaticamente pelo ModelForm
        # (não precisas tratar manualmente aqui, a menos que queiras lógica extra)

        if commit:
            user.save()

        return user


class SaldoForm(forms.Form):
    valor = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)

class ApostaForm(forms.ModelForm):
    class Meta:
        model = Aposta
        fields = ['jogador', 'tipo_aposta', 'odds', 'valor_apostado']

        
class ApostaMultiplaForm(forms.ModelForm):
    class Meta:
        model = ApostaMultipla
        fields = ['valor_apostado', 'apostas']

    def clean(self):
        cleaned_data = super().clean()
        valor_apostado = cleaned_data.get('valor_apostado')
        apostas = cleaned_data.get('apostas')

        if not apostas:
            raise forms.ValidationError("Você deve escolher pelo menos uma aposta.")

        # Calcular a odd total e os possíveis ganhos
        multipla = ApostaMultipla.objects.create(user=self.instance.user, valor_apostado=valor_apostado)
        for aposta in apostas:
            multipla.apostas.add(aposta)

        multipla.calcular_odd_total()  # Calculando a odd total e os ganhos possíveis

        return cleaned_data
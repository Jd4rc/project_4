from django import forms

from mailings.models import Client, Mailing, Message


class StyleFormMixin:
    """Bootstrap-классы полям формы. Один раз здесь — чтобы в шаблонах
    не было ручной вёрстки каждого поля."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class ClientForm(StyleFormMixin, forms.ModelForm):
    class Meta:
        model = Client
        # owner не редактируется руками: заполнится из request.user (блок 1).
        fields = ('full_name', 'email', 'comment')
        widgets = {'comment': forms.Textarea(attrs={'rows': 3})}


class MessageForm(StyleFormMixin, forms.ModelForm):
    class Meta:
        model = Message
        fields = ('subject', 'body')
        widgets = {'body': forms.Textarea(attrs={'rows': 8})}


def _datetime_field(label):
    """Поле под <input type="datetime-local">.

    Браузер присылает '2026-09-29T14:30', а в стандартных форматах Django
    такого нет — без явного input_formats форма молча ругается «введите дату».
    """
    return forms.DateTimeField(
        label=label,
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'],
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M',
        ),
    )


class MailingForm(StyleFormMixin, forms.ModelForm):
    first_sent_at = _datetime_field('Дата и время первой отправки')
    finished_at = _datetime_field('Дата и время окончания отправки')

    class Meta:
        model = Mailing
        # status в форме нет: его ставит система (R7) — отправка и фоновая задача.
        fields = ('message', 'clients', 'first_sent_at', 'finished_at')

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('first_sent_at')
        end = cleaned_data.get('finished_at')
        if start and end and end <= start:
            self.add_error('finished_at', 'Окончание должно быть позже первой отправки.')
        return cleaned_data

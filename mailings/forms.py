from django import forms

from mailings.models import Client


class StyleFormMixin:
    """Bootstrap-классы полям формы. Один раз здесь — чтобы в шаблонах
    не было ручной вёрстки каждого поля."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class ClientForm(StyleFormMixin, forms.ModelForm):
    class Meta:
        model = Client
        # owner не редактируется руками: заполнится из request.user (блок 1).
        fields = ('full_name', 'email', 'comment')
        widgets = {'comment': forms.Textarea(attrs={'rows': 3})}

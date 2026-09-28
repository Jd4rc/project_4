from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Главная. Статистика (R17-R19) появится в блоке 6."""

    template_name = 'mailings/home.html'

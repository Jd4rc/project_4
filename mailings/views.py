from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from mailings.forms import ClientForm, MailingForm, MessageForm
from mailings.models import Client, Mailing, Message


class HomeView(TemplateView):
    """Главная. Статистика (R17-R19) появится в блоке 6."""

    template_name = 'mailings/home.html'


class ClientListView(ListView):
    """Список получателей (R2). Шаблон выводится сам: mailings/client_list.html."""

    model = Client
    paginate_by = 20


class ClientDetailView(DetailView):
    model = Client


class ClientCreateView(CreateView):
    model = Client
    form_class = ClientForm


class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm


class ClientDeleteView(DeleteView):
    model = Client
    success_url = reverse_lazy('mailings:client_list')


class MessageListView(ListView):
    """Список сообщений (R4). Шаблон — mailings/message_list.html."""

    model = Message
    paginate_by = 20


class MessageDetailView(DetailView):
    model = Message


class MessageCreateView(CreateView):
    model = Message
    form_class = MessageForm


class MessageUpdateView(UpdateView):
    model = Message
    form_class = MessageForm


class MessageDeleteView(DeleteView):
    model = Message
    success_url = reverse_lazy('mailings:message_list')


class MailingListView(ListView):
    """Список рассылок (R6)."""

    model = Mailing
    paginate_by = 20

    def get_queryset(self):
        # Статус хранится в базе, поэтому между запусками фоновой задачи он врёт.
        # Один UPDATE перед выборкой — и список не показывает «Запущена» там,
        # где время окончания уже прошло (решение по Q3).
        Mailing.objects.finish_expired()
        return super().get_queryset().select_related('message')


class MailingDetailView(DetailView):
    model = Mailing


class MailingCreateView(CreateView):
    model = Mailing
    form_class = MailingForm


class MailingUpdateView(UpdateView):
    model = Mailing
    form_class = MailingForm


class MailingDeleteView(DeleteView):
    model = Mailing
    success_url = reverse_lazy('mailings:mailing_list')

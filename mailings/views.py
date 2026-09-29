from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from mailings.forms import ClientForm, MessageForm
from mailings.models import Client, Message


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

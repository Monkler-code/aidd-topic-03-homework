"""Views for share management."""

from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, View, UpdateView

from .forms import ShareModelForm
from .models import Share
from .services.graph import get_graph
from django.contrib.auth.mixins import UserPassesTestMixin


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    """Mixin that restricts access to authenticated users only."""

    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return render(
            status=403,
            template_name="user/auth.html",
            context={"error": "Необходима авторизация для выполнения этого действия."},
        )


class ShareListView(ListView):
    """List all shares with pagination."""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView(View):
    """Show share details with price chart."""

    @staticmethod
    def get(request, pk):
        share = get_object_or_404(Share, id=pk)
        plot_div = get_graph(share)
        return render(request, "dashboard/detail.html", {"share": share, "plot_div": plot_div})


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Create a new share."""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Update an existing share."""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Delete a share."""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")
    context_object_name = "share"

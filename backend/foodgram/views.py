from django.shortcuts import render
from django.views.generic import TemplateView
from django.conf import settings
from django.http import Http404

def page_not_found(request, exception):
    return render(request, '404.html', status=404)

class StaticPageView(TemplateView):
    def get(self, request, *args, **kwargs):
        if not settings.STATIC_PAGES_ENABLED:
            raise Http404("Страница временно недоступна")
        return super().get(request, *args, **kwargs)

class AboutView(StaticPageView):
    template_name = 'about.html'

class TechnologiesView(StaticPageView):
    template_name = 'technologies.html' 
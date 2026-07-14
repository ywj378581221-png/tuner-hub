from django.conf import settings
from django.http import FileResponse, Http404


def frontend_app(_request):
    index_file = settings.BASE_DIR / 'static' / 'index.html'
    if not index_file.exists():
        raise Http404('Frontend has not been built yet.')
    return FileResponse(index_file.open('rb'), content_type='text/html')

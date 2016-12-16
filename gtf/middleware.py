import os
import errno
from six.moves.urllib.parse import urlparse, urljoin
import warnings
import itertools

from collections import defaultdict

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token
from django.core.exceptions import ImproperlyConfigured
from django.core import urlresolvers
from django.utils.encoding import iri_to_uri

try:
    from django.contrib.sites.shortcuts import get_current_site
except ImportError:
    # django < 1.9
    from django.contrib.sites.models import get_current_site


@requires_csrf_token
def generic_template_finder_view(request, base_path='', extra_context={}):
    """
    Find a template based on the request url and render it.

    * ``/`` -> ``index.html``
    * ``/foo/`` -> ``foo.html`` OR ``foo/index.html``
    """
    path = base_path + request.path
    if not path.endswith('/'):
        path += '/'
    possibilities = (
            path.strip('/') + '.html',
            path.lstrip('/') + 'index.html',
            path.strip('/'),
            )
    for t in possibilities:
        try:
            response = render(request, t, extra_context)
        except (TemplateDoesNotExist):
            continue
        except OSError as e:
            # If there's a directory that matches the template we're looking for,
            # Django will raise a `IsADirectoryError` in `render` instead of a
            # `TemplateDoesNotExist` error. IsADirectoryError was introduced in
            # Python 3 and is a subclass of OSError and its errno corresponds to EISDIR,
            # so for Python 2 compatibility, OSError is caught instead of IsADirectoryError
            if e.errno == errno.EISDIR:
                continue
            else:
                raise
        if t.endswith('.html') and not path.endswith(request.path) and settings.APPEND_SLASH:
            # Emulate what CommonMiddleware does and redirect, only if:
            # - the template we found ends in .html
            # - the path has been modified (slash appended)
            # - and settings.APPEND_SLASH is True
            return HttpResponsePermanentRedirect(path)
        return response
    raise Http404('Template not found in any of %r' % (possibilities,))


class GenericTemplateFinderMiddleware(object):
    """
    Response middleware that uses :func:`generic_template_finder_view` to attempt to
    autolocate a template for otherwise 404 responses.
    """
    def process_response(self, request, response):
        """
        Ensures that
        404 raised from view functions are not caught by
        ``GenericTemplateFinderMiddleware``.
        """
        if response.status_code == 404 and not getattr(request, '_generic_template_finder_middleware_view_found', False):
            try:
                if hasattr(request, 'urlconf'):
                    # Django calls response middlewares after it has unset the
                    # request's urlconf. Set it temporarily so the template can
                    # reverse properly.
                    urlresolvers.set_urlconf(request.urlconf)
                return generic_template_finder_view(request, extra_context=self.get_extra_context(request))
            except Http404:
                return response
            except UnicodeEncodeError:
                return response
            finally:
                urlresolvers.set_urlconf(None)
        else:
            return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Informs :func:`process_response` that there was a view for this url and that
        it threw a real 404.
        """
        request._generic_template_finder_middleware_view_found = True

    def get_extra_context(self, request):
        return {}

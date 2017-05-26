import errno
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token
from django.core import urlresolvers

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # If new style middleware isn't supported, just inherit from object
    MiddlewareMixin = object


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


class GenericTemplateFinderMiddleware(MiddlewareMixin):
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
        real_404 = getattr(request, '_generic_template_finder_middleware_view_found', False)
        if response.status_code == 404 and not real_404:
            try:
                if hasattr(request, 'urlconf'):
                    # Django calls response middlewares after it has unset the
                    # request's urlconf. Set it temporarily so the template can
                    # reverse properly.
                    urlresolvers.set_urlconf(request.urlconf)
                return generic_template_finder_view(
                    request,
                    extra_context=self.get_extra_context(request)
                )
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

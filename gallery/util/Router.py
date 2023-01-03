"""Utility class to simplify url designation."""

from django.urls import path


class Router:
    """Utility class to simplify url designation."""

    def __init__(self):
        self.links = []

    def __call__(self, route, kwargs=None, name=None):

        def bind(view):
            if hasattr(view, 'as_view'):
                view_ = view.as_view()
            else:
                view_ = view

            self.links.append(
                path(route, view_, kwargs, name)
            )

            return view

        return bind

    def collect(self):
        return self.links

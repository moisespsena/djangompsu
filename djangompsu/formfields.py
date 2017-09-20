from django import forms
from pagedown.widgets import AdminPagedownWidget


class MarkdownFormField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(MarkdownFormField, self).__init__(*args, **kwargs)
        self.widget = AdminPagedownWidget()

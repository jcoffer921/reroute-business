from django import forms

from .models import BlogPost


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["title", "content", "journal_tag"]
        labels = {
            "content": "Body",
            "journal_tag": "Tag",
        }
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Entry title"}),
            "content": forms.Textarea(attrs={"rows": 12, "placeholder": "Write your reflections..."}),
            "journal_tag": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["journal_tag"].required = False
        self.fields["journal_tag"].choices = [("", "Select a tag (optional)")] + list(
            BlogPost.JOURNAL_TAG_CHOICES
        )

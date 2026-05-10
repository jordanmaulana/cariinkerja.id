from django import forms

INPUT_CLS = "w-full px-3 py-2 border rounded text-sm"


class SmtpTestForm(forms.Form):
    to = forms.EmailField(
        label="Recipient",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CLS, "placeholder": "you@example.com"}
        ),
    )
    subject = forms.CharField(
        max_length=200,
        initial="cariinkerja.id SMTP test",
        widget=forms.TextInput(attrs={"class": INPUT_CLS}),
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": INPUT_CLS, "rows": 6}),
        initial="This is a test email from the cariinkerja.id admin SMTP test page.",
    )

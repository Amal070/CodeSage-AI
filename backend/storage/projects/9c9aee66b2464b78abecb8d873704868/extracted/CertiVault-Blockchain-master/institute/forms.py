from django import forms
from .models import InstituteCertificate


class InstituteCertificateForm(forms.ModelForm):
    class Meta:
        model = InstituteCertificate
        fields = [
            'student_email',
            'student_name',
            'register_number',
            'course',
            'year_of_passing',
            'certificate_file',
        ]

    def clean_certificate_file(self):
        f = self.cleaned_data.get('certificate_file')
        if f and f.content_type != 'application/pdf':
            raise forms.ValidationError('Only PDF files are allowed for certificates.')
        return f

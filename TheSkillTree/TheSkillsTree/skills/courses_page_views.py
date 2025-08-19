from django.shortcuts import render
from django.http import FileResponse
import os

def math_page_view(request):
    return render(request, 'skills/CoursesPage/Math/math.html')


def public_speaking_page_view(request):
    return render(request, 'skills/CoursesPage/PublicSpeaking/publicspeking.html')

def download_pdf(request, grade):
    pdf_directory = 'pdf file path'
    pdf_file = f'grade_{grade}_curriculum.pdf'

    file_path = os.path.join(pdf_directory, pdf_file)
    
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=pdf_file)

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_pdf_from_content(content):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer,pagesize=letter)
    pdf.drawString(100, 750 , content)
    pdf.showPage()
    pdf.save()
    
    buffer.seek(0)
    return buffer
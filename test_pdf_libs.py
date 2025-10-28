"""
Quick test to verify PDF generation libraries are working correctly.
"""

def test_reportlab():
    """Test ReportLab PDF generation"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # Create a PDF in memory
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "ReportLab Test - R&D Tax Credit Report")
        c.save()
        
        # Check if PDF was created
        buffer.seek(0)
        pdf_content = buffer.read()
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b'%PDF')
        
        print("✓ ReportLab is working correctly!")
        return True
    except Exception as e:
        print(f"✗ ReportLab test failed: {e}")
        return False


def test_xhtml2pdf():
    """Test xhtml2pdf HTML to PDF conversion"""
    try:
        from xhtml2pdf import pisa
        import io
        
        # Simple HTML content
        html_content = """
        <html>
        <head><title>Test Report</title></head>
        <body>
            <h1>R&D Tax Credit Audit Report</h1>
            <p>This is a test of xhtml2pdf library.</p>
        </body>
        </html>
        """
        
        # Create PDF from HTML
        buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=buffer)
        
        # Check if PDF was created successfully
        assert not pisa_status.err
        buffer.seek(0)
        pdf_content = buffer.read()
        assert len(pdf_content) > 0
        assert pdf_content.startswith(b'%PDF')
        
        print("✓ xhtml2pdf is working correctly!")
        return True
    except Exception as e:
        print(f"✗ xhtml2pdf test failed: {e}")
        return False


def test_pillow():
    """Test Pillow image handling"""
    try:
        from PIL import Image
        import io
        
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='blue')
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        
        # Verify image was created
        buffer.seek(0)
        assert len(buffer.read()) > 0
        
        print("✓ Pillow is working correctly!")
        return True
    except Exception as e:
        print(f"✗ Pillow test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing PDF generation dependencies...\n")
    
    results = []
    results.append(test_reportlab())
    results.append(test_xhtml2pdf())
    results.append(test_pillow())
    
    print(f"\n{'='*50}")
    if all(results):
        print("✓ All PDF generation dependencies are working!")
    else:
        print("✗ Some dependencies failed. Please check the errors above.")
    print('='*50)

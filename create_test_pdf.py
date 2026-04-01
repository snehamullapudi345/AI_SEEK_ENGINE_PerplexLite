from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("helvetica", size=12)
pdf.cell(200, 10, text="RISE AI Assistant - Test Document", new_x="LMARGIN", new_y="NEXT", align='C')
pdf.cell(200, 10, text="The secret code for this test is: APPLE123", new_x="LMARGIN", new_y="NEXT", align='L')
pdf.cell(200, 10, text="This PDF will be used to verify the RAG system.", new_x="LMARGIN", new_y="NEXT", align='L')
pdf.output("test_document.pdf")
print("PDF created successfully: test_document.pdf")

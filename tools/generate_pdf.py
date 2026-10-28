import subprocess
import os
import shutil
import pypdf

HTML_PATH = r"c:\Users\shiv shanker\Downloads\brandproof\docs\submission_pdf.html"
DOCS_PDF = r"c:\Users\shiv shanker\Downloads\brandproof\docs\BrandProof_Round2_Submission.pdf"
DOWNLOADS_PDF = r"c:\Users\shiv shanker\Downloads\BrandProof_Round2_Submission.pdf"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    print(f"HTML size: {len(html)} bytes")
    print(f"Number of page containers: {html.count('page-container')}")

    cmd = [
        EDGE_EXE,
        "--headless=new",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={DOCS_PDF}",
        HTML_PATH,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(DOCS_PDF):
        size = os.path.getsize(DOCS_PDF)
        reader = pypdf.PdfReader(DOCS_PDF)
        print(f"Generated PDF: {size} bytes, {len(reader.pages)} pages")
        shutil.copy2(DOCS_PDF, DOWNLOADS_PDF)
        print(f"Copied to {DOWNLOADS_PDF}")
    else:
        print("Failed to generate PDF")

if __name__ == "__main__":
    main()

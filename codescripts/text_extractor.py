from PyPDF2 import PdfReader
from typing import Optional
import re,docx
from utils.s3_operations import S3Helper
import os, hashlib

TMP_DIR = '/tmp'
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

class ExtractText:        
    def remove_formatting(self, text: str) -> str:
        text = re.sub(r'[\n\t\r]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def get_text(self, path: str) -> Optional[str]:
        '''
        Extracts text from the given file and returns a plain string containing content.
        
        Args:
        path (str): The path of the PDF/DOCX files.
        
        Returns:
        str: A plain string containing text content, or None if the files cannot be read.
        '''
        print(f"\n--- Started text extraction ---\n")
        extracted_text = ""
        try:
                if path.startswith('s3://'):
                # Extract the S3 bucket and object key
                    s3_bucket = path.split('/')[2]
                    s3_helper = S3Helper(s3_bucket)
                    s3_key = '/'.join(path.split('/')[3:])
                    local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
                    # Download the file from S3
                    s3_helper.download_file_from_s3(s3_key, local_file_path)
                    path = local_file_path
                    
                if path.lower().endswith('.pdf'):
                    content = PdfReader(path)
                    pdf_text = ""
                    for page in content.pages:
                        try:
                            pdf_text += page.extract_text()
                        except:
                            return None
                    pdf_text = self.remove_formatting(pdf_text)
                    extracted_text += pdf_text
                    extracted_text += '\n'
                    print(pdf_text[:500])
                    print(f"--- PDF text extraction completed---")

                elif path.lower().endswith('.docx'):
                    doc = docx.Document(path)
                    fullText = []
                    for para in doc.paragraphs:
                        fullText.append(para.text)
                    doc_text = '\n'.join(fullText)
                    doc_text = self.remove_formatting(doc_text)
                    print(doc_text[:500])
                    print(f"--- DOCX text extraction completed---")
                    extracted_text += doc_text
                    extracted_text += '\n'

        except Exception as e:
            print("Exception in get_text():   ", e)
            return None
        finally:
            return extracted_text
        
    def hash_text(self, text: str) -> str:
        '''
        Generates a hash for the given text.
        
        Args:
        text (str): The text to be hashed.
        
        Returns:
        str: A hash of the text.
        '''
        return hashlib.sha256(text.encode('utf-8')).hexdigest() if text else ''
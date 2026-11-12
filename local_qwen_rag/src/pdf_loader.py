import os
import pdfplumber
from pypdf import PdfReader
from src.logger_config import log


def safe_extract_page_text(pdfplumber_page, file_path, page_idx):
    try:
        text = pdfplumber_page.extract_text()
        if text and text.strip():
            return text.strip() + "\n"
    except Exception as e:
        print(f"[警告] pdfplumber解析第{page_idx + 1}页失败，切换pypdf兜底: {str(e)}")
        log.warning(f"pdfplumber解析第{page_idx + 1}页失败[{str(e)}]，切换pypdf兜底")

    try:
        reader = PdfReader(file_path)
        text = reader.pages[page_idx].extract_text()
        if text and text.strip():
            return text.strip() + "\n"
    except Exception as e2:
        print(f"[警告] pypdf兜底读取第{page_idx + 1}页失败: {str(e2)}")
        log.warning(f"pypdf兜底读取第{page_idx + 1}页也失败: {str(e2)}")
    return ""


def load_all_pdf(raw_pdf_dir: str) -> list[dict]:
    docs = []
    doc_id = 0
    if not os.path.exists(raw_pdf_dir):
        print(f"[警告] PDF目录不存在: {raw_pdf_dir}")
        log.warning(f"PDF目录不存在: {raw_pdf_dir}")
        return docs

    pdf_files = [f for f in os.listdir(raw_pdf_dir) if f.lower().endswith(".pdf")]
    print(f"  扫描到待处理PDF文件总数: {len(pdf_files)}")
    for idx, file in enumerate(pdf_files):
        file_path = os.path.join(raw_pdf_dir, file)
        full_text = ""
        print(f"\n[处理进度 {idx + 1}/{len(pdf_files)}] 正在打开文件: {file}")

        try:
            pdf = pdfplumber.open(file_path)
        except Exception as open_err:
            print(f"[错误] pdfplumber打开失败，切换纯pypdf读取: {str(open_err)}")
            log.error(f"打开 {file} 失败(字体元数据损坏): {str(open_err)}，改用纯pypdf读取全文")
            try:
                reader = PdfReader(file_path)
                for page_idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        full_text += t.strip() + "\n"
                print(f"  pypdf读取完成，文本长度: {len(full_text)}")
            except Exception as e:
                print(f"[错误] pypdf读取{file}失败: {str(e)}")
                log.error(f"pypdf读取{file}也失败: {str(e)}")
            if full_text.strip():
                docs.append({
                    "doc_id": doc_id,
                    "file_name": file,
                    "content": full_text.strip()
                })
                print(f"✅ {file} 兜底加载成功")
                log.info(f"兜底读取PDF: {file}, 文本长度: {len(full_text)}")
                doc_id += 1
            continue

        # pdfplumber打开成功
        page_count = len(pdf.pages)
        print(f"  文件总页数: {page_count}，逐页提取文本...")
        try:
            for page_idx, page in enumerate(pdf.pages):
                page_content = safe_extract_page_text(page, file_path, page_idx)
                full_text += page_content
        except Exception as page_err:
            print(f"[警告] 遍历页面异常: {str(page_err)}")
            log.warning(f"遍历{file}页面异常: {str(page_err)}")
        finally:
            pdf.close()

        if full_text.strip():
            docs.append({
                "doc_id": doc_id,
                "file_name": file,
                "content": full_text.strip()
            })
            print(f"✅ {file} 加载完成，有效文本长度: {len(full_text)}")
            log.info(f"成功加载PDF: {file}, 有效文本长度: {len(full_text)}")
            doc_id += 1
        else:
            print(f"[警告] {file} 未提取到任何有效文本")
            log.warning(f"{file} 未提取到任何有效文本")
    return docs
from pathlib import Path
import io, os
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 5
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff'}

app = FastAPI(title='ТехПаспорт API', version='1.0.0', description='API загрузки и проверки чертежей')
allowed_origins = os.getenv('CORS_ORIGINS', '*').split(',')
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False, allow_methods=['GET','POST','OPTIONS'], allow_headers=['*'])


def validate_file(name: str, content: bytes):
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Неподдерживаемый формат. Разрешены PDF, PNG, JPG/JPEG, TIFF.')
    if not content:
        raise ValueError('Файл пустой.')
    if len(content) > MAX_FILE_BYTES:
        raise ValueError('Размер файла превышает 20 МБ.')
    if ext == '.pdf':
        if not content.startswith(b'%PDF-'):
            raise ValueError('Файл с расширением PDF не является корректным PDF.')
        try:
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ValueError('Зашифрованные PDF не поддерживаются.')
            pages = len(reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('Не удалось прочитать PDF-файл.') from exc
        if pages < 1:
            raise ValueError('В PDF нет страниц.')
        if pages > MAX_PDF_PAGES:
            raise ValueError(f'В PDF {pages} страниц, максимум — {MAX_PDF_PAGES}.')
        return pages
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            pages = getattr(image, 'n_frames', 1) if ext in {'.tif', '.tiff'} else 1
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Файл изображения повреждён или имеет неверный формат.') from exc
    if pages > MAX_PDF_PAGES:
        raise ValueError(f'В TIFF {pages} страниц, максимум — {MAX_PDF_PAGES}.')
    return pages


@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'ТехПаспорт API'}


@app.post('/api/upload-files')
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail='Выберите хотя бы один файл.')
    results, errors = [], []
    for upload in files:
        name = Path(upload.filename or 'unnamed').name
        try:
            content = await upload.read(MAX_FILE_BYTES + 1)
            pages = validate_file(name, content)
            results.append({'name': name, 'size': len(content), 'pages': pages, 'status': 'validated'})
        except ValueError as exc:
            errors.append({'name': name, 'error': str(exc)})
        finally:
            await upload.close()
    if not results:
        raise HTTPException(status_code=422, detail='Ни один файл не прошёл проверку: ' + '; '.join(f"{e['name']}: {e['error']}" for e in errors))
    return {'files': results, 'rejected': errors, 'accepted_count': len(results), 'rejected_count': len(errors), 'note': 'Файлы проверены; OCR/LLM распознавание не выполняется.'}


@app.get('/')
def index():
    return FileResponse(BASE_DIR / 'index.html')

# Serves any local frontend assets (if present), e.g. sample images.
app.mount('/assets', StaticFiles(directory=BASE_DIR, check_dir=True), name='assets')

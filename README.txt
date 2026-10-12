ТехПаспорт — сайт с backend API

Локальный запуск без Docker:
1. Установите Python 3.12+.
2. В терминале из папки site выполните:
   python -m venv .venv
   source .venv/bin/activate       (Windows: .venv\\Scripts\\activate)
   pip install -r requirements.txt
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
3. Откройте http://localhost:8000
4. Проверка API: http://localhost:8000/docs и http://localhost:8000/api/health

Запуск через Docker:
   docker build -t tehpasport .
   docker run --rm -p 8000:8000 tehpasport
Затем откройте http://localhost:8000

Деплой:
- Выложите содержимое папки site в GitHub.
- На Render создайте Web Service из репозитория. render.yaml / Dockerfile настроены для запуска.
- После деплоя проверьте /api/health.

API:
POST /api/upload-files — multipart/form-data, поле files можно повторять для нескольких файлов.
GET /api/health — health check.

Проверки на сервере:
- форматы PDF, PNG, JPG/JPEG, TIFF;
- размер каждого файла до 20 МБ;
- PDF и многостраничный TIFF до 5 страниц;
- проверка целостности файлов и чтение числа страниц.

Важно: сейчас backend валидирует загруженные файлы и возвращает метаданные. OCR/LLM, хранение файлов и база данных ещё не подключены. Не загружайте чувствительные производственные документы в публичный демо-деплой без настройки доступа, логирования и политики хранения.

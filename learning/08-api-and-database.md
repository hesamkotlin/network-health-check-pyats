<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۶: پیاده‌سازی REST API با FastAPI و دیتابیس SQLite (`08-api-and-database.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

- **FastAPI:** محبوب‌ترین و مدرن‌ترین وب‌فریم‌ورک Python برای ساخت **REST API** است که بر پایه `Type Hints` پایتون، کتابخانه اعتبارسنجی **`Pydantic`** و سرور ناهمگام **`ASGI (Uvicorn)`** کار می‌کند و به صورت خودکار مستندات تعاملی **Swagger / OpenAPI (`/docs`)** تولید می‌کند.
- **SQLite (`sqlite3`):** موتور دیتابیس رابطه‌ای (`Relational SQL Database`) سبک و بدون نیاز به سرور مجزا که در کتابخانه استاندارد Python تعبیه شده است (دقیقاً همان موتور دیتابیسی که در **Android Room** روی گوشی استفاده می‌کنید!).

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

در یک تیم مهندسی واقعی، اجرای دستی اسکریپت در ترمینال کافی نیست؛ داشبوردهای مانیتورینگ، پایپ‌لاین‌های CI/CD یا اپلیکیشن‌های موبایل باید بتوانند:
1. از طریق یک درخواست HTTP (`POST /api/v1/runs`) اجرای تست سلامت شبکه را استارت بزنند.
2. وضعیت و نتیجه تست (`GET /api/v1/runs/{run_id}`) را دریافت کنند.
3. تاریخچه تست‌های قبلی (`GET /api/v1/runs`) را از دیتابیس SQLite بخوانند تا روند سلامت شبکه در طول زمان مشخص باشد.

---

## 3. How does it work? (چطور کار می‌کند؟)

معماری ما در فاز ۶ دقیقاً از الگوی **Clean Architecture / Layered Architecture** پیروی می‌کند تا منطق وب (`FastAPI`) هرگز با منطق اجرای تست (`pyATS / Genie`) یا دیتابیس (`SQLite`) قاطی نشود:

```text
HTTP Client / Dashboard
        │
        ▼  JSON Request / Response
FastAPI Endpoints (api/app.py -> create_fastapi_app)
        │
        ▼  Calls Application Service
HealthCheckExecutionService (api/app.py)
        ├──► 1. Runs Network Check (core/concurrency.py -> execute_single_device_check)
        └──► 2. Persists & Queries History (database/repository.py -> SQLiteHealthRepository)
```

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم + نکات مصاحبه فنی)

- **Pydantic `BaseModel`:** کلاسی در FastAPI که بدنه درخواست JSON (`Request Body`) را به صورت خودکار اعتبارسنجی (`Validate`) و پارس می‌کند (معادل `@Serializable data class` در Kotlin به همراه Validator داخلی). اگر کلاینت مقدار نامعتبری بفرستد، FastAPI به طور خودکار کد **`422 Unprocessable Entity`** برمی‌گرداند.
- **Parameterized SQL Queries (`?`):** در `sqlite3`، همیشه مقادیر را با علامت سؤال `WHERE run_id = ?` و یک Tuple پاس می‌دهیم تا جلوی حملات **SQL Injection** به طور ۱۰۰٪ گرفته شود (معادل `@Query("SELECT * FROM runs WHERE run_id = :runId")` در Android Room).
- **Separation of Concerns (قانون فاز ۶):** چرا نباید از یک ORM سنگین مثل SQLAlchemy در نسخه اول یک پروژه کوچک استفاده کنیم؟ چون جدول ما یک جدول تاریخچه ساده (`test_runs`) است و استفاده مستقیم از `sqlite3` با الگوی **Repository**، کد را شفاف، سریع و بدون پیچیدگی اضافه نگه می‌دارد.

> **💡 نکته طلایی مصاحبه فنی (تفاوت FastAPI با Flask و Django):**
> اگر در مصاحبه پرسیدند: *«چرا FastAPI را انتخاب کردید؟»*
> به ۳ مورد اشاره کنید:
> ۱. **Data Validation خودکار با Pydantic** بر اساس Python Type Hints.
> ۲. **پشتیبانی بومی از `async / await` (استاندارد ASGI)** برای توان عملیاتی بالا در سرویس‌های I/O-bound.
> ۳. **تولید خودکار مستندات OpenAPI / Swagger UI** در مسیر `/docs`.

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`src/network_health/database/repository.py`**: پیاده‌سازی کلاس `SQLiteHealthRepository` برای ساخت جدول `test_runs`، ذخیره گزارش (`save_report`)، دریافت وضعیت (`get_run_status`)، بازسازی گزارش کامل (`get_report`) و دریافت تاریخچه (`list_history`).
- **`src/network_health/api/app.py`**: پیاده‌سازی سرویس هماهنگ‌کننده `HealthCheckExecutionService` و کارخانه ساخت برنامه FastAPI (`create_fastapi_app`).

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی)

1. **`SQLiteHealthRepository._init_schema()` (`repository.py`)**:
   جدول `test_runs` را در صورت عدم وجود (`CREATE TABLE IF NOT EXISTS`) ایجاد می‌کند.
2. **`SQLiteHealthRepository.save_report(report, status)` (`repository.py`)**:
   اطلاعات خلاصه گزارش را در ستون‌های SQL و جزئیات assertions را به صورت JSON در ستون `results_json` ذخیره می‌کند.
3. **`HealthCheckExecutionService` (`api/app.py`)**:
   لایه میانی بین API و موتور تست؛ تست را اجرا کرده و نتیجه را در `SQLiteHealthRepository` ذخیره می‌کند.
4. **چهار Endpoint اصلی REST در `create_fastapi_app()` (`api/app.py`)**:
   - `POST /api/v1/runs` (کد `201 Created`): شروع یک تست جدید.
   - `GET /api/v1/runs/{run_id}/status`: دریافت وضعیت و خلاصه تعداد تست‌های پاس/رد شده.
   - `GET /api/v1/runs/{run_id}`: دریافت گزارش کامل شامل تمام Assertions.
   - `GET /api/v1/runs`: دریافت لیست تاریخچه آخرین اجراها.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام اجرای یک درخواست API)

1. کلاینت درخواست `POST /api/v1/runs` با بدنه `{"hostname": "sim-rtr-core-01", "scenario": "healthy"}` می‌فرستد.
2. مدل Pydantic (`StartRunRequest`) بررسی می‌کند که `scenario` حتماً یکی از مقادیر مجاز (`healthy`, `unhealthy`, `unreachable`) باشد.
3. متد `app_service.start_test_run()` فراخوانی می‌شود.
4. تابع `execute_single_device_check()` وضعیت دستگاه را جمع‌آوری و اعتبارسنجی کرده و یک `HealthCheckReport` می‌سازد.
5. متد `repository.save_report(report)` گزارش را با یک `run_id` یکتا (UUID) در فایل SQLite ذخیره می‌کند.
6. پاسخ JSON با کد `201 Created` به کلاینت برگردانده می‌شود.

---

## 8. Real code examples (مثال واقعی کار با سرویس و دیتابیس SQLite)

```python
from network_health.api.app import HealthCheckExecutionService
from network_health.database.repository import SQLiteHealthRepository

repo = SQLiteHealthRepository("reports/network_health_history.db")
service = HealthCheckExecutionService(repository=repo)

# 1. Start a test run
run_data = service.start_test_run(hostname="sim-rtr-core-01", scenario="healthy")
run_id = run_data["run_id"]

# 2. Query status by run_id
print(service.get_run_status(run_id))

# 3. Query execution history
print("Total runs in history:", len(service.get_run_history()))
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **استفاده از `f-string` در ساخت کوئری‌های SQL (آسیب‌پذیری SQL Injection):**
   - **غلط:** `conn.execute(f"SELECT * FROM test_runs WHERE run_id = '{run_id}'")`
   - **درست:** `conn.execute("SELECT * FROM test_runs WHERE run_id = ?", (run_id,))`
2. **فراموش کردن `conn.commit()` یا Context Manager (`with self._connect() as conn:`):**
   - بدون `commit()`، تراکنش‌های `INSERT` روی فایل SQLite نهایی نمی‌شوند.

---

## 10. Practical exercises (تمرین‌های عملی)

تست واحد دیتابیس SQLite و سرویس اجرا را در ترمینال اجرا کنید:
```bash
.venv/bin/pytest src/network_health/tests/test_advanced_phases.py -k "sqlite"
```

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

تست `test_sqlite_repository_and_execution_service` دو سناریوی `healthy` و `unhealthy` را اجرا کرده، در SQLite ذخیره می‌کند، وضعیت و تاریخچه را می‌خواند و با نتیجه **`PASSED`** به پایان می‌رسد.

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** چرا در کوئری‌های SQLite از علامت `?` (`Parameterized Query`) به جای چسباندن رشته‌ها (`f-string`) استفاده می‌کنیم؟
2. **سؤال ۲:** وظیفه کتابخانه `Pydantic` در `FastAPI` چیست و اگر ورودی نامعتبر باشد چه کد وضعیتی (`HTTP Status Code`) برمی‌گرداند؟

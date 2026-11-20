<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۷: هم‌زمانی در Python — مقایسه Threading، Multiprocessing و Asyncio (`09-concurrency.md`)

> **🔥 مهم‌ترین مبحث مصاحبه‌های فنی Python:**
> تقریباً در ۱۰۰٪ مصاحبه‌های فنی پایتون و بک‌اند از شما درباره **GIL (Global Interpreter Lock)** و تفاوت **`Threading`**، **`Multiprocessing`** و **`Asyncio`** سؤال می‌پرسند. این مستند را با دقت مطالعه کنید!

---

## 1. What is this technology? (این تکنولوژی چیست؟)

پایتون ۳ مدل استاندارد برای اجرای هم‌زمان (`Concurrency` و `Parallelism`) دارد که هر سه را در فایل [src/network_health/core/concurrency.py](file:///Users/hesam/.gemini/antigravity/scratch/network-health-check/src/network_health/core/concurrency.py) پیاده‌سازی کرده‌ایم:

| مدل در Python | معادل در Kotlin / Android | مناسب برای چه نوع کاری؟ | وضعیت در برابر Python GIL |
| :--- | :--- | :--- | :--- |
| **`Threading`** (`ThreadPoolExecutor`) | `Dispatchers.IO` (OS Threads) | **I/O-Bound** (مثل اتصال SSH به ۵۰ روتر، خواندن فایل، درخواست شبکه) | همه Threadها در یک پروسه هستند؛ در حین انتظار شبکه/دیسک، **GIL آزاد می‌شود** و هم‌زمانی واقعی رخ می‌دهد. |
| **`Multiprocessing`** (`ProcessPoolExecutor`) | اجرای چند پروسه جداگانه در OS | **CPU-Bound** (مثل پارس کردن سنگین میلیون‌ها خط لاگ یا پردازش تصویر) | هر پروسه مفسر Python و **GIL مستقل خودش** را دارد و روی چند هسته CPU به صورت **Parallel** اجرا می‌شود. |
| **`Asyncio`** (`async / await`) | **Kotlin Coroutines** روی یک Event Loop تک‌نخی | **High-Concurrency I/O** (هزاران سوکت ناهمگام، وب‌سرور FastAPI) | تک‌نخی (`Single-Threaded Cooperative Multitasking`)؛ نیازمند کتابخانه‌های غیرمسدودکننده یا `asyncio.to_thread()`. |

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

فرض کنید به جای ۱ روتر، باید سلامت **۱۰۰ روتر** را بررسی کنیم و اتصال SSH و اجرای دستورات روی هر روتر ۵ ثانیه طول می‌کشد:
- **اجرای ترتیبی (`Sequential`):** `100 × 5 = 500` ثانیه (بیش از ۸ دقیقه!).
- **اجرای هم‌زمان (`Concurrent` با ۲۰ Worker):** کل ۱۰۰ روتر در حدود **۲۵ ثانیه** بررسی می‌شوند!

علاوه بر سرعت، در تست هم‌زمان چند دستگاه دو نیاز حیاتی داریم:
1. **مدیریت Timeout (`Connection Timeout Handling`):** اگر روتر شماره ۷ هنگ کرد، نباید کل برنامه برای همیشه منتظر بماند.
2. **ایزوله‌سازی خطا (`Error Isolation`):** اگر روتر شماره ۷ با خطا مواجه شد، تست ۹۹ روتر دیگر نباید کرش کند؛ بلکه باید برای روتر ۷ یک گزارش با وضعیت `TestOutcome.ERROR` ثبت شود و بقیه روترها کارشان را تمام کنند.

---

## 3. How does it work? (چطور کار می‌کند؟)

### ۱. راز مهم مصاحبه: **GIL (Global Interpreter Lock)** چیست؟
در مفسر استاندارد پایتون (`CPython`)، یک قفل سراسری به نام **GIL** وجود دارد که اجازه می‌دهد در هر لحظه فقط **یک Thread** بایت‌کد پایتون را روی CPU اجرا کند.
- **پس چرا `Threading` در اتوماسیون شبکه عالی کار می‌کند؟**
  چون وقتی یک Thread منتظر پاسخ شبکه (SSH به روتر یا پاسخ HTTP) می‌ماند، مفسر پایتون **GIL را آزاد می‌کند (`Releases the GIL during I/O`)** تا Threadهای دیگر به روترهای دیگر دستور بفرستند!
- **کی باید سراغ `Multiprocessing` برویم؟**
  وقتی کار ما ۱۰۰٪ محاسباتی روی CPU است (`CPU-Bound`) و می‌خواهیم از تمام هسته‌های پردازنده (`Multi-Core CPU`) به صورت موازی استفاده کنیم.

### ۲. دام خطرناک در `Asyncio` (قانون فاز ۷ پروژه):
> **آیا قرار دادن یک تابع همگام (`Synchronous`) مثل `pyATS` یا `time.sleep()` مستقیماً داخل یک تابع `async def` آن را ناهمگام (`Asynchronous`) می‌کند؟**
> **خیر! هرگز!**
اگر یک تابع مسدودکننده (`Blocking Function`) را مستقیم داخل `async def` صدا بزنید، کل **Event Loop** تک‌نخی متوقف (`Block`) می‌شود و هیچ کار دیگری به صورت هم‌زمان انجام نمی‌شود!
**راه‌حل استاندارد در Python 3.9+:** استفاده از **`await asyncio.to_thread(sync_func, arg)`** (دقیقاً معادل `withContext(Dispatchers.IO) { ... }` در کاتلین!) که کار مسدودکننده را بدون قفل کردن Event Loop به یک Thread پس‌زمینه می‌فرستد.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **GIL (Global Interpreter Lock):** قفل سطح مفسر CPython برای مدیریت امن حافظه (`Reference Counting`).
- **I/O-Bound vs CPU-Bound:** کارهایی که زمانشان صرف انتظار شبکه/دیسک می‌شود در برابر کارهایی که زمانشان صرف محاسبات پردازنده می‌شود.
- **`Future` Object:** نماینده نتیجه‌ای که در آینده آماده می‌شود (معادل `Deferred<T>` در Kotlin Coroutines).
- **Error Isolation:** مهار استثناهای هر دستگاه به صورت جداگانه تا خرابی یک روتر باعث شکست کل Batch نشود.

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`src/network_health/core/concurrency.py`**: پیاده‌سازی هر سه روش هم‌زمانی (`run_checks_with_threading`, `run_checks_with_multiprocessing`, `run_checks_with_asyncio`) به همراه ایزوله‌سازی خطا و مدیریت Timeout.
- **`src/network_health/tests/test_advanced_phases.py`**: تست‌های خودکار هر سه مدل هم‌زمانی.

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی در `concurrency.py`)

1. **`DeviceCheckTarget`**: مدل تغییرناپذیر (`@dataclass(frozen=True)`) که مشخصات روتر هدف (`hostname`, `policy_path`, `scenario`) را نگه می‌دارد (قابل Serialize شدن برای ارسال بین پروسه‌ها در `Multiprocessing`).
2. **`execute_single_device_check(target)`**: تابع Worker که سلامت یک دستگاه را بررسی می‌کند و هر استثنای پیش‌بینی‌نشده‌ای را با `_build_error_report()` مهار می‌کند.
3. **`run_checks_with_threading(targets, max_workers, timeout_seconds)`**:
   از `ThreadPoolExecutor` و `future.result(timeout=...)` استفاده می‌کند.
4. **`run_checks_with_multiprocessing(targets, max_workers, timeout_seconds)`**:
   از `ProcessPoolExecutor` برای توزیع کار بین پروسه‌های مستقل سیستم‌عامل استفاده می‌کند.
5. **`run_checks_with_asyncio(targets, timeout_seconds)`**:
   از `asyncio.gather()` به همراه `asyncio.wait_for(asyncio.to_thread(...), timeout=...)` استفاده می‌کند.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام اجرای هم‌زمان در `Asyncio`)

```text
run_checks_with_asyncio([target1, target2, target3])
  │
  ├─► Creates 3 Coroutines (_async_check_one_device)
  │
  ├─► asyncio.gather(*tasks) schedules all 3 concurrently
  │     ├── Task 1 ──► asyncio.to_thread(execute_single_device_check, target1)
  │     ├── Task 2 ──► asyncio.to_thread(execute_single_device_check, target2)
  │     └── Task 3 ──► asyncio.to_thread(execute_single_device_check, target3)
  │
  └─► Aggregates all 3 HealthCheckReports in order (with per-device timeout & error isolation)
```

---

## 8. Real code examples (مثال واقعی از کدهای `concurrency.py`)

```python
async def _async_check_one_device(
    target: DeviceCheckTarget,
    timeout_seconds: float,
) -> HealthCheckReport:
    """Offload synchronous pyATS/Genie check to a background thread safely inside asyncio."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(execute_single_device_check, target),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        return _build_error_report(
            target=target,
            error_category="async_timeout",
            error_message=f"Async check for '{target.hostname}' timed out after {timeout_seconds}s.",
        )
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **فراخوانی مستقیم کد مسدودکننده داخل `async def` بدون `asyncio.to_thread`:**
   - باعث فریز شدن Event Loop می‌شود.
2. **ارسال اشیاء غیرقابل Pickling (مثل سوکت باز SSH) به `ProcessPoolExecutor`:**
   - در `Multiprocessing`، آرگومان‌ها و خروجی‌ها باید بین پروسه‌های سیستم‌عامل کپی (`Pickle / Serialize`) شوند. به همین دلیل ما یک `@dataclass` سبک به نام `DeviceCheckTarget` به پروسه فرزند می‌فرستیم و یک `@dataclass` به نام `HealthCheckReport` تحویل می‌گیریم.

---

## 10. Practical exercises (تمرین‌های عملی)

تست‌های هر سه مدل هم‌زمانی (`Threading`, `Multiprocessing`, `Asyncio`) را اجرا کنید:
```bash
.venv/bin/pytest src/network_health/tests/test_advanced_phases.py -k "concurrent"
```

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

هر سه تست (`test_concurrent_device_checks_with_threading`, `test_concurrent_device_checks_with_multiprocessing`, `test_concurrent_device_checks_with_asyncio`) با وضعیت **`PASSED`** اجرا می‌شوند.

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش و مصاحبه)

1. **سؤال ۱ (مصاحبه):** چرا با وجود **GIL** در پایتون، استفاده از `Threading` برای اتصال SSH به ۱۰۰ روتر باعث افزایش شدید سرعت می‌شود؟
2. **سؤال ۲ (مصاحبه):** چرا قرار دادن مستقیم یک تابع همگام (`Synchronous`) داخل `async def` آن را ناهمگام نمی‌کند و راه‌حل استاندارد آن چیست؟

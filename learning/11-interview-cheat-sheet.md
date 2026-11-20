<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.9; font-family: -apple-system, BlinkMacSystemFont, "Vazirmatn", "IRANSans", "Tahoma", sans-serif; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td, blockquote { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# 🎯 تقلب‌نامه جامع مصاحبه فنی (`11-interview-cheat-sheet.md`)
**پروژه: Network Health Check Automation System (Python + Cisco pyATS + FastAPI + Docker)**

---

## ۱. معرفی ۲ دقیقه‌ای پروژه در شروع مصاحبه (Elevator Pitch)

اگر مصاحبه‌گر گفت: **«درباره پروژه پایتون و اتوماسیون شبکه‌ات توضیح بده»**، دقیقاً این ۵ مورد را به ترتیب بگویید:

1. **معماری کلی (`Modular Monolith`):**
   «من یک سیستم **Network Health Check Automation** با معماری **Modular Monolith** و اصول **Clean Architecture** نوشتم که وضعیت واقعی روترهای سیسکو (`Actual State`) را با وضعیت استاندارد مورد انتظار در فایل‌های YAML (`Expected State`) مقایسه می‌کند و گزارش `PASS / FAIL` تولید می‌کند.»
2. **لایه Core Domain (بدون وابستگی به شبکه):**
   «مدل‌های داده (`InterfaceState`, `RouteEntry`, `DeviceSnapshot`) را با `@dataclass(frozen=True)` و `Type Hints` به صورت کاملاً تغییرناپذیر (`Immutable`) طراحی کردم و منطق اعتبارسنجی را با توابع خالص (`Pure Functions`) نوشتم تا ۱۰۰٪ قابل تست واحد (`Unit Test`) باشد.»
3. **جداسازی شبیه‌ساز آفلاین از روتر واقعی (`ABC` و `Dependency Inversion`):**
   «یک رابط انتزاعی (`NetworkDeviceConnector`) با `ABC` ساختم که دو پیاده‌سازی دارد:
   - یکی شبیه‌ساز آفلاین (`SimulatedIosXeDevice`) که خروجی‌های CLI ضبط‌شده را از فایل‌های JSON می‌خواند تا در CI/CD بدون نیاز به روتر فیزیکی تست شود.
   - و دیگری کانکتور واقعی (`PyAtsRealDeviceConnector`) که با **Cisco Unicon (SSH)** و متغیرهای محیطی امن (`%ENV{...}`) به روتر واقعی در **Cisco DevNet Sandbox** وصل می‌شود.»
4. **پارس کردن خروجی روتر با `Cisco Genie`:**
   «به جای نوشتن Regexهای شکننده دستی، از Parserهای رسمی **Cisco Genie** برای دستورات `show interfaces` و `show ip route` استفاده کردم و دیکشنری خروجی Genie را به Domain Modelهای خودم Map کردم.»
5. **هم‌زمانی (`Concurrency`)، دیتابیس (`SQLite`) و `FastAPI`:**
   «برای تست هم‌زمان چند روتر از `ThreadPoolExecutor` و `asyncio.to_thread` همراه با **Timeout** و **Error Isolation** استفاده کردم، تاریخچه اجراها را با **Parameterized SQL** در **SQLite** ذخیره کردم و کل سیستم را با **FastAPI** و **Docker** کانتینرایز کردم.»

---

## ۲. سؤالات طلایی مصاحبه: هم‌زمانی در پایتون (`GIL`, `Threading`, `Multiprocessing`, `Asyncio`)

### سؤال ۱: قفل `GIL (Global Interpreter Lock)` در پایتون چیست؟
- **پاسخ کوتاه و دقیق:**
  «در مفسر استاندارد پایتون (`CPython`)، قفل **GIL** یک Mutex در سطح مفسر است که اجازه می‌دهد در هر پروسه، در هر لحظه **فقط یک Thread** بایت‌کد پایتون را روی CPU اجرا کند (تا مدیریت حافظه `Reference Counting` امن بماند).»

### سؤال ۲: با وجود GIL، چرا برای SSH زدن به ۱۰۰ روتر از `Threading` استفاده می‌کنیم و سرعت چند برابر می‌شود؟
- **پاسخ کوتاه و دقیق:**
  «چون اتصال شبکه و SSH یک کار **I/O-Bound** است نه **CPU-Bound**. در پایتون به محض اینکه یک Thread منتظر پاسخ شبکه یا دیسک می‌ماند، **مفسر پایتون قفل GIL را آزاد می‌کند (`Releases GIL during I/O`)** و Threadهای بعدی بلافاصله به روترهای دیگر درخواست می‌فرستند. اما اگر کار ما محاسبات سنگین روی پردازنده (**CPU-Bound**) باشد، باید از **`Multiprocessing` (`ProcessPoolExecutor`)** استفاده کنیم تا هر پروسه مفسر و GIL مستقل خودش را روی هسته‌های مختلف CPU داشته باشد.»

### سؤال ۳: اگر یک تابع قدیمی و Synchronous (مثل اجرای دستور در `pyATS`) را مستقیم داخل یک تابع `async def` صدا بزنیم چه اتفاقی می‌افتد؟
- **پاسخ کوتاه و دقیق:**
  «صرفِ گذاشتن یک تابع Synchronous داخل `async def` آن را ناهمگام نمی‌کند! چون `asyncio` روی یک **Event Loop تک‌نخی** کار می‌کند، فراخوانی مستقیم تابع مسدودکننده باعث **قفل شدن کل Event Loop** می‌شود. راه‌حل استاندارد این است که آن تابع را با **`await asyncio.to_thread(sync_func, arg)`** به یک Thread پس‌زمینه بفرستیم تا Event Loop آزاد بماند.»

### جدول مقایسه سریع هم‌زمانی (پایتون در برابر کاتلین)

| مدل در Python | معادل در Kotlin | کاربرد اصلی | وضعیت GIL |
| :--- | :--- | :--- | :--- |
| `ThreadPoolExecutor` (`Threading`) | `Dispatchers.IO` | کارهای **I/O-Bound** (شبکه، SSH، دیسک) | در زمان انتظار شبکه آزاد می‌شود |
| `ProcessPoolExecutor` (`Multiprocessing`) | چند پروسه مجزای OS | کارهای **CPU-Bound** (پردازش سنگین) | هر پروسه GIL مستقل خودش را دارد |
| `asyncio` (`async / await`) | `Kotlin Coroutines` | هزاران درخواست شبکه ناهمگام (`FastAPI`) | تک‌نخی؛ کدهای مسدودکننده نیاز به `asyncio.to_thread` دارند |

---

## ۳. سؤالات طلایی مصاحبه: `FastAPI`، `Pydantic` و دیتابیس `SQLite`

### سؤال ۴: چرا `FastAPI` را به جای `Flask` یا `Django` انتخاب کردید؟
- **پاسخ کوتاه و دقیق:**
  1. **اعتبارسنجی خودکار ورودی و خروجی با `Pydantic`** بر اساس Python Type Hints.
  2. **برگرداندن خودکار کد وضعیت `422 Unprocessable Entity`** در صورت نامعتبر بودن JSON ورودی، قبل از وارد شدن به منطق برنامه.
  3. **پشتیبانی بومی از `async / await` (استاندارد `ASGI` و وب‌سرور `Uvicorn`)** و تولید خودکار مستندات **Swagger UI (`/docs`)**.

### سؤال ۵: چرا در کوئری‌های SQL نباید از `f-string` استفاده کنیم و راه‌حل چیست؟
- **پاسخ کوتاه و دقیق:**
  «استفاده از `f-string` برای قرار دادن ورودی کاربر در رشته SQL باعث آسیب‌پذیری خطرناک **SQL Injection** می‌شود، چون مفسر دیتابیس ممکن است ورودی کاربر را به عنوان بخشی از دستور SQL اجرا کند. راه‌حل استاندارد استفاده از **Parameterized Queries** با علامت سؤال (`WHERE run_id = ?`) است تا درایور دیتابیس ورودی را صرفاً به عنوان یک مقدار داده (`Literal`) ببیند.»

---

## ۴. سؤالات طلایی مصاحبه: معماری، `Docker` و `Microservices`

### سؤال ۶: چرا پروژه را با `Modular Monolith` شروع کردید نه `Microservices`؟
- **پاسخ کوتاه و دقیق:**
  «در مقیاس اولیه، Microservices باعث **Over-Engineering**، تاخیر شبکه بین سرویس‌ها (`Network Latency`) و پیچیدگی استقرار می‌شود. در **Modular Monolith**، همه ماژول‌ها در یک پروسه و در حافظه با هم کار می‌کنند و Latency نزدیک به صفر است، اما چون مرز پکیج‌ها (`api`, `core`, `devices`, `database`) کاملاً تفکیک شده است، هر زمان تعداد دستگاه‌ها بسیار زیاد شد، به‌راحتی می‌توانیم `api-service` را از `test-execution-worker` جدا کنیم.»

### سؤال ۷: چرا وقتی وب‌سرور پایتون (`uvicorn`) را داخل کانتینر Docker اجرا می‌کنیم باید حتماً `--host 0.0.0.0` بدهیم نه `127.0.0.1`؟
- **پاسخ کوتاه و دقیق:**
  «چون هر کانتینر Docker شبکه مجازی و `localhost` ایزوله خودش را دارد. اگر وب‌سرور داخل کانتینر به `127.0.0.1` گوش بدهد، فقط از داخل خودِ همان کانتینر قابل دسترسی است و درخواست‌های بیرون کانتینر به آن نمی‌رسند. با `--host 0.0.0.0` روی تمام اینترفیس‌های شبکه کانتینر گوش می‌دهد.»

---

## ۵. سؤالات طلایی مصاحبه: مبانی پایتون و شبکه (`pyATS / Genie / Unicon`)

### سؤال ۸: چرا در `@dataclass` پایتون برای فیلدهای دیکشنری یا لیست نباید بنویسیم `interfaces: dict = {}` و باید از `field(default_factory=dict)` استفاده کنیم؟
- **پاسخ کوتاه و دقیق:**
  «چون در پایتون مقادیر پیش‌فرض فقط یک بار در زمان تعریف کلاس در حافظه ساخته می‌شوند. اگر از یک شیء قابل تغییر (`Mutable`) مثل `{}` یا `[]` به عنوان مقدار پیش‌فرض مستقیم استفاده کنیم، تمام نمونه‌های کلاس به همان یک دیکشنری مشترک در حافظه اشاره می‌کنند. اما `field(default_factory=dict)` تضمین می‌کند به ازای هر نمونه جدید، یک دیکشنری تازه ساخته شود.»

### سؤال ۹: نقش ۳ جزء اصلی اکوسیستم Сиسکو (`pyATS Core`، `Genie` و `Unicon`) چیست؟
- **پاسخ کوتاه و دقیق:**
  1. **`pyATS Core (AEtest / Easypy)`:** فریم‌ورک اجرای چرخه حیات تست (`CommonSetup` -> `Testcases` -> `CommonCleanup`) و گزارش‌گیری (معادل JUnit در کاتلین).
  2. **`Genie`:** کتابخانه پارس کردن خروجی متنی دستورات CLI روتر به دیکشنری ساختاریافته پایتون (معادل Gson/Moshi برای خط فرمان روتر). با دادن `output=raw_text` به `device.parse()` می‌توان از آن ۱۰۰٪ آفلاین هم استفاده کرد.
  3. **`Unicon`:** موتور اتصال SSH/Telnet به روتر که یک **State Machine** هوشمند برای مدیریت Promptهای مختلف روتر و صفحه‌بندی (`--More--`) دارد.

### سؤال ۱۰: در جدول مسیریابی روتر (`show ip route`)، چه زمانی یک مسیر مستقیم متصل (`Connected / C`) از جدول حذف می‌شود؟
- **پاسخ کوتاه و دقیق:**
  «جدول مسیریابی فقط مسیرهای فعال و قابل استفاده را نگه می‌دارد. به محض اینکه اینترفیس مربوط به آن شبکه خاموش (`shutdown / down`) شود یا کابل آن قطع شود، روتر بلافاصله مسیر `Connected (C)` آن پورت را از جدول مسیریابی حذف می‌کند.»

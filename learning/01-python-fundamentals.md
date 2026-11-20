<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۱: مبانی مهندسی Python برای توسعه‌دهندگان Kotlin (`01-python-fundamentals.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

زبان **Python** یک زبان برنامه‌نویسی سطح بالا، مفسری (`Interpreted`)، با تایپ پویا (`Dynamically Typed`) اما قوی (`Strongly Typed`) است که در نسخه ۳.۵ به بعد از سیستم `Type Hints` (`PEP 484`) نیز پشتیبانی می‌کند.

برای یک مهندس **Android / Kotlin**، مهم‌ترین تفاوت ذهنی این است که در Kotlin بررسی نوع داده‌ها در زمان کامپایل (`Compile-Time`) توسط کامپایلر انجام می‌شود، اما در Python نوع متغیرها در زمان اجرا (`Runtime`) به خودِ شیء (`Object`) متصل است و `Type Hints` به IDE و ابزارهای Static Analysis کمک می‌کنند تا کد را مثل Kotlin ایمن نگه دارند.

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

Python زبان استاندارد و بلامنازع دنیای **Network Automation** و فریم‌ورک **Cisco pyATS** است. در پروژه **Network Health Check** ما از ویژگی‌های مدرن Python برای موارد زیر استفاده می‌کنیم:
- مدل‌سازی وضعیت اینترفیس‌ها و جدول مسیریابی با `@dataclass(frozen=True)` (معادل `data class` در Kotlin).
- تعریف وضعیت‌های مجاز با `Enum` (مانند `InterfaceAdminStatus`, `TestOutcome`).
- نگهداری و پردازش سریع داده‌های شبکه با ساختمان‌داده‌های داخلی (`list`, `dict`, `tuple`, `set`).
- تعریف قراردادهای انتزاعی با `ABC` (معادل `interface` در Kotlin).
- مدیریت خطای صریح و سلسله‌مراتبی با `Custom Exceptions`.

---

## 3. How does it work? (چطور کار می‌کند؟)

مفسر Python کدهای فایل‌های `.py` را به بایت‌کد (`.pyc` در پوشه `__pycache__`) تبدیل کرده و روی ماشین مجازی Python (`PVM`) اجرا می‌کند. هر فایل `.py` یک **Module** است و هر پوشه‌ای که حاوی فایل `__init__.py` باشد یک **Package** محسوب می‌شود.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم با مقایسه Kotlin)

### الف) Variables, Data Types & Type Hints
در Python نیازی به کلیدواژه `val` یا `var` نیست؛ نام متغیر به همراه `Type Hint` نوشته می‌شود:

```python
# Kotlin: val hostname: String = "sim-rtr-core-01"
hostname: str = "sim-rtr-core-01"

# Kotlin: val prefixLength: Int? = 24
prefix_length: int | None = 24

# Kotlin: val isHealthy: Boolean = true
is_healthy: bool = True
```

### ب) Collections: `list`, `dict`, `tuple`, `set`

| ساختار در Python | معادل در Kotlin | ویژگی کلیدی و کاربرد در Network Health Check |
| :--- | :--- | :--- |
| `list[T]` (`[...]`) | `MutableList<T>` | لیست مرتب و قابل تغییر؛ مناسب برای جمع‌آوری `assertions` در حین اجرای تست‌ها. |
| `tuple[T, ...]` (`(...)`) | `List<T>` (Immutable) | دنباله مرتب و **تغییرناپذیر (`Immutable`)**؛ مناسب برای نگهداری قوانین ثابت (`interfaces: tuple[ExpectedInterfaceRule, ...]`). |
| `dict[K, V]` (`{k: v}`) | `MutableMap<K, V>` | نگاشت کلید به مقدار با جستجوی `O(1)`؛ مناسب برای دسترسی سریع به اینترفیس‌ها با نام آن‌ها (`interfaces["GigabitEthernet1"]`). |
| `set[T]` (`{...}`) | `MutableSet<T>` | مجموعه بدون تکرار با عملیات مجموعه‌ای سریع؛ مناسب برای استخراج نام اینترفیس‌های الزامی (`required_interface_names`). |

### ج) Functions
توابع با کلیدواژه `def` تعریف می‌شوند و می‌توانند مقادیر پیش‌فرض (`Default Arguments`) و آرگومان‌های نام‌گذاری‌شده (`Named Arguments`) داشته باشند (دقیقاً مشابه Kotlin):

```python
def validate_device_availability(
    snapshot: DeviceSnapshot,
    policy: ExpectedDeviceHealthPolicy,
) -> CheckAssertionResult:
    ...
```

### د) Classes, Objects, `@dataclass`, Inheritance & Composition
- **`@dataclass(frozen=True)`**: معادل مستقیم `data class` با فیلدهای `val` در Kotlin است. متدهای `__init__` (سازنده)، `__eq__` (`equals`)، `__hash__` (`hashCode`) و `__repr__` (`toString`) را خودکار تولید می‌کند.
- **Inheritance (`ارث‌بری`)**: کلاس `SimulatedIosXeDevice(NetworkDeviceConnector)` از کلاس پایه انتزاعی `NetworkDeviceConnector(ABC)` ارث‌بری می‌کند.
- **Composition (`ترکیب`)**: کلاس `DeviceSnapshot` شامل مجموعه‌ای از اشیاء `InterfaceState` و `RouteEntry` است (`has-a relationship`).

### هـ) Exception Handling
به جای `try / catch / finally` در Kotlin، در Python از `try / except / else / finally` استفاده می‌کنیم و با کلیدواژه `raise` (معادل `throw` در Kotlin) استثنا پرتاب می‌کنیم:

```python
try:
    with path.open("r", encoding="utf-8") as handle:
        raw_data = yaml.safe_load(handle)
except yaml.YAMLError as exc:
    raise ConfigurationError(f"Failed to parse YAML: {exc}") from exc
```

---

## 5. Explanation of each relevant source file (توضیح فایل‌های منبع مرتبط)

1. **`src/network_health/core/exceptions.py`**:
   سلسله‌مراتب خطاهای دامنه (`NetworkHealthError`, `ConfigurationError`, `DeviceConnectionError`, `CommandExecutionError`, `ValidationError`) را تعریف می‌کند.
2. **`src/network_health/core/models.py`**:
   تمامی مدل‌های داده تغییرناپذیر پروژه (`InterfaceState`, `RouteEntry`, `DeviceSnapshot`, `ExpectedDeviceHealthPolicy`, `CheckAssertionResult`, `HealthCheckReport`) و `Enum`ها را پیاده‌سازی می‌کند.
3. **`src/network_health/core/config.py`**:
   فایل YAML سیاست سلامت شبکه (`test_data/expected_health_policy.yaml`) را خوانده، اعتبارسنجی کرده و به شیء `ExpectedDeviceHealthPolicy` تبدیل می‌کند.
4. **`src/network_health/core/validators.py`**:
   توابع خالص (`Pure Functions`) اعتبارسنجی که وضعیت واقعی (`DeviceSnapshot`) را با وضعیت مورد انتظار (`ExpectedDeviceHealthPolicy`) مقایسه می‌کنند.
5. **`src/network_health/devices/base.py`**:
   قرارداد انتزاعی `NetworkDeviceConnector(ABC)` را برای جداسازی شبیه‌ساز آفلاین از اتصال واقعی تعریف می‌کند.

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی)

- **`InterfaceState` (`models.py`)**:
  وضعیت یک اینترفیس شبکه را نگه می‌دارد و دارای دو `@property` محاسباتی (`is_healthy` و `cidr`) است (معادل Custom Getter در Kotlin: `val isHealthy: Boolean get() = ...`).
- **`ExpectedDeviceHealthPolicy.required_interface_names` (`models.py`)**:
  با استفاده از **Set Comprehension** (`{rule.name for rule in self.interfaces}`) مجموعه‌ای یکتا از نام اینترفیس‌های مورد انتظار برمی‌گرداند.
- **`load_health_policy(policy_path)` (`config.py`)**:
  با استفاده از `pathlib.Path` و Context Manager (`with path.open(...)`) فایل YAML را به صورت ایمن باز کرده و پس از اتمام بلوک، فایل را خودکار می‌بندد (معادل `.use { ... }` در Kotlin).
- **`evaluate_device_health(snapshot, policy)` (`validators.py`)**:
  تمامی قوانین اینترفیس‌ها، IPها و مسیرهای مسیریابی را اجرا کرده و یک `HealthCheckReport` کامل تولید می‌کند.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام اجرا در لایه Core)

1. تابع `load_health_policy` فایل `test_data/expected_health_policy.yaml` را می‌خواند.
2. تابع `parse_health_policy_dict` دیکشنری خام YAML را به اشیاء تایپ‌شده `ExpectedInterfaceRule` و `ExpectedRouteRule` داخل یک `tuple` تغییرناپذیر تبدیل می‌کند.
3. یک شیء `DeviceSnapshot` (شامل `dict[str, InterfaceState]` و `dict[str, RouteEntry]`) به تابع `evaluate_device_health` داده می‌شود.
4. توابع `validate_device_availability`, `validate_interface_status`, `validate_interface_ip` و `validate_route_entry` به ترتیب اجرا شده و اشیاء `CheckAssertionResult` تولید می‌کنند.
5. اگر تمامی نتایج `TestOutcome.PASS` باشند، وضعیت کلی گزارش (`overall_outcome`) برابر `PASS` و در غیر این صورت `FAIL` ثبت می‌شود.

---

## 8. Real code examples (مثال واقعی از کدهای پروژه)

```python
from network_health.core.models import (
    InterfaceAdminStatus,
    InterfaceOperStatus,
    InterfaceState,
)

# Constructing an immutable dataclass instance with named arguments
gig1 = InterfaceState(
    name="GigabitEthernet1",
    ip_address="10.10.20.1",
    prefix_length=24,
    admin_status=InterfaceAdminStatus.UP,
    oper_status=InterfaceOperStatus.UP,
    enabled=True,
)

print(gig1.cidr)        # Output: 10.10.20.1/24
print(gig1.is_healthy)  # Output: True
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **استفاده از `list` یا `dict` به عنوان مقدار پیش‌فرض آرگومان تابع یا فیلد `@dataclass`:**
   - **خطا:** در Python آرگومان‌های پیش‌فرض فقط یک بار در زمان تعریف تابع ارزیابی می‌شوند!
   - **راه‌حل:** در `@dataclass` همیشه از `field(default_factory=dict)` یا `field(default_factory=list)` استفاده کنید (همانند کلاس `DeviceSnapshot` در `models.py`).
2. **فراموش کردن `from __future__ import annotations` در Python 3.9:**
   - **خطا:** نوشتن `str | None` در Python 3.9 بدون این دستور باعث `TypeError: unsupported operand type(s) for |` در زمان اجرا می‌شود.
   - **راه‌حل:** قرار دادن `from __future__ import annotations` در ابتدای تمامی فایل‌های پروژه.

---

## 10. Practical exercises (تمرین‌های عملی)

### تمرین ۱: ساخت و بررسی `InterfaceState` در مفسر تعاملی
دستور زیر را در ترمینال اجرا کنید تا یک اینترفیس `DOWN` بسازید و وضعیت سلامت آن را بررسی کنید:
```bash
PYTHONPATH=src .venv/bin/python -c "
from network_health.core.models import InterfaceState, InterfaceAdminStatus, InterfaceOperStatus
iface = InterfaceState(
    name='GigabitEthernet3',
    ip_address='192.168.1.1',
    prefix_length=24,
    admin_status=InterfaceAdminStatus.DOWN,
    oper_status=InterfaceOperStatus.DOWN,
    enabled=False,
)
print('CIDR:', iface.cidr)
print('Is Healthy:', iface.is_healthy)
"
```

### تمرین ۲: بررسی تغییرناپذیری (`Immutability`)
تلاش کنید مقدار `iface.ip_address = "10.0.0.1"` را تغییر دهید و خطای `FrozenInstanceError` را مشاهده کنید.

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

- **نتیجه تمرین ۱:**
  ```text
  CIDR: 192.168.1.1/24
  Is Healthy: False
  ```
- **نتیجه تمرین ۲:**
  پرتاب استثنای `dataclasses.FrozenInstanceError: cannot assign to field 'ip_address'` که ثابت می‌کند مدل‌های دامنه ما همانند `val` در `data class` زبان Kotlin در برابر تغییرات ناخواسته محافظت شده‌اند.

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** دکوراتور `@dataclass(frozen=True)` در Python معادل چه ساختاری در Kotlin است و چه متدهایی را خودکار تولید می‌کند؟
2. **سؤال ۲:** تفاوت `tuple` و `list` در Python چیست و چرا در `ExpectedDeviceHealthPolicy` از `tuple[ExpectedInterfaceRule, ...]` استفاده کردیم؟
3. **سؤال ۳:** عبارت `{rule.name for rule in self.interfaces}` چه نوع ساختمان‌داده‌ای تولید می‌کند؟
4. **سؤال ۴:** چرا در Python هنگام پرتاب استثنای جدید در بلوک `except` از سینتکس `raise ConfigurationError(...) from exc` استفاده می‌کنیم؟

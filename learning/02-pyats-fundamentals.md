<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۲ (بخش اول): مبانی فریم‌ورک Cisco pyATS (`02-pyats-fundamentals.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

**Cisco pyATS (Python Automated Test System)** یک اکوسیستم و فریم‌ورک جامع تست و اتوماسیون شبکه است که در ابتدا توسط مهندسان Cisco برای تست سیستم‌عامل‌های شبکه (`IOS-XE`, `NX-OS`, `IOS-XR`) توسعه یافت و سپس به صورت عمومی منتشر شد.

اکوسیستم **pyATS** از سه لایه اصلی تشکیل شده است:
1. **pyATS Core Framework (`AEtest`, `Easypy`, `Topology`)**: موتور اجرای تست، مدیریت چرخه حیات تست (`Setup / Test / Cleanup`)، و گزارش‌گیری.
2. **Genie (`pyats[library]`)**: کتابخانه استاندارد مدل‌سازی شبکه و دارای هزاران **CLI Parser** رسمی برای تبدیل خروجی متنی دستورات روتر و سوییچ به دیکشنری‌های ساختاریافته Python.
3. **Unicon**: موتور مدیریت اتصال (`SSH`, `Telnet`, `Console`) و مدیریت State Machine خط فرمان دستگاه‌های شبکه.

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

در مهندسی شبکه سنتی، مهندسان به صورت دستی به روتر SSH می‌زنند، دستور `show ip interface brief` یا `show ip route` را اجرا می‌کنند و چشمی خروجی را می‌خوانند. این روش مقیاس‌پذیر نیست و مستعد خطای انسانی است.

ما به **pyATS** نیاز داریم تا:
- وضعیت شبکه را به شکل **Automated Test Cases** (مشابه تست‌های JUnit در اندروید) تعریف کنیم.
- چرخه حیات تست (`CommonSetup` -> `Testcases` -> `CommonCleanup`) را استاندارد کنیم.
- نتایج استاندارد `PASS`, `FAIL`, `SKIPPED`, `ERRORED` و گزارش‌های دقیق تولید کنیم.

---

## 3. How does it work? (چطور کار می‌کند؟)

### تفاوت کلیدی: Framework vs Library (با مقایسه Android / Kotlin)
- **Library (کتابخانه):** کدی که **شما** آن را صدا می‌زنید (مثل `Retrofit` یا `PyYAML` یا `Genie Parser`). جریان کنترل برنامه در دست کد شماست.
- **Framework (فریم‌ورک):** موتوری که **کد شما را صدا می‌زند** (**Inversion of Control** — دقیقاً مثل چرخه حیات `Activity / Fragment` در Android یا موتور اجرای تست `JUnit 5`). در `pyATS AEtest`، شما کلاس‌های `CommonSetup`, `Testcase`, و `CommonCleanup` را تعریف می‌کنید و این موتور `aetest.main()` است که آن‌ها را به ترتیب کشف و اجرا می‌کند.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **AEtest (Automated Execution Test):** زیرسیستم تعریف و اجرای اسکریپت‌های تست در pyATS (معادل **JUnit** در Kotlin).
- **Easypy (`pyats run job`):** اجراکننده سطح بالا (`Job Runner`) که یک یا چند اسکریپت AEtest را اجرا کرده و آرشیو لاگ و گزارش کلی تولید می‌کند (معادل Gradle Test Runner).
- **Testbed:** فایل YAML که توپولوژی شبکه، دستگاه‌ها (`Devices`)، اینترفیس‌ها و روش‌های اتصال را توصیف می‌کند.
- **Section Results:** وضعیت نهایی هر بخش تست در pyATS:
  - `Passed`: تمامی بررسی‌ها موفق بوده‌اند.
  - `Failed`: حداقل یک بررسی (`Assertion`) با شکست مواجه شده است.
  - `Errored`: یک استثنای پیش‌بینی‌نشده (`Unhandled Exception`) رخ داده است.
  - `Skipped`: اجرای بخش به دلیل پیش‌نیاز نامعتبر (مثلاً در دسترس نبودن دستگاه) رد شده است.

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`src/network_health/tests/aetest_health_check.py`**: اسکریپت اصلی تست که از کلاس‌های رسمی `pyats.aetest` استفاده می‌کند.
- **`src/network_health/tests/health_check_job.py`**: فایل Job برای اجرای اسکریپت تست از طریق دستور استاندارد `pyats run job`.
- **`testbed/devices.yaml.example`**: فایل تعریف Testbed استاندارد pyATS.

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی)

- **`pyats.aetest.CommonSetup`**: کلاسی که یک بار در ابتدای اسکریپت تست اجرا می‌شود تا پیش‌نیازها (بارگذاری Testbed، بارگذاری Policy، و دریافت Snapshot دستگاه) را آماده کند.
- **`pyats.aetest.Testcase`**: کلاس پایه برای هر سناریوی تست مستقل (`DeviceAvailabilityTestcase`, `InterfaceHealthTestcase`, `RoutingTableTestcase`).
- **`pyats.aetest.CommonCleanup`**: کلاسی که همیشه در پایان اسکریپت تست اجرا می‌شود تا گزارش‌های JSON/Markdown را ذخیره کرده و اتصال دستگاه را ببندد.
- **`pyats.easypy.run()`**: تابع داخل `health_check_job.py` که یک TestScript را در قالب یک Task اجرا می‌کند.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام اجرای pyATS در پروژه)

```text
[aetest.main() / pyats run job]
       │
       ▼
1. CommonSetup
   ├── @subsection load_policy_and_testbed
   └── @subsection connect_and_collect_snapshot
       │  (Stores `policy`, `testbed`, `snapshot` in `self.parent.parameters`)
       ▼
2. DeviceAvailabilityTestcase
   └── @test verify_device_reachability_and_hostname
       ▼
3. InterfaceHealthTestcase
   ├── @setup check_interfaces_present
   ├── @test  verify_interfaces_operational_status
   └── @test  verify_interfaces_ipv4_configuration
       ▼
4. RoutingTableTestcase
   ├── @setup check_routing_table_available
   └── @test  verify_expected_routes
       ▼
5. CommonCleanup
   └── @subsection generate_reports_and_disconnect
```

---

## 8. Real code examples (مثال‌های واقعی دستورات و کد)

### بررسی نسخه نصب‌شده pyATS و Genie
```bash
.venv/bin/pyats version check
```

### اجرای مستقیم اسکریپت AEtest
```bash
PYTHONPATH=src .venv/bin/python src/network_health/tests/aetest_health_check.py --scenario healthy
```

### اجرای Job از طریق Easypy CLI
```bash
PYTHONPATH=src .venv/bin/pyats run job src/network_health/tests/health_check_job.py --no-archive
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **تعریف بیش از یک `CommonSetup` یا `CommonCleanup` در یک فایل تست:**
   - در هر اسکریپت `AEtest` حداکثر یک کلاس `CommonSetup` و یک کلاس `CommonCleanup` مجاز است.
2. **استفاده از `assert` خام به جای متدهای نتیجه AEtest (`self.passed()`, `self.failed()`, `self.skipped()`):**
   - هرچند `assert` در صورت شکست باعث شکست تست می‌شود، اما استفاده صریح از `self.failed("reason")` و `self.passed("reason")` پیام دقیق مهندسی را در جدول گزارش خروجی pyATS ثبت می‌کند.

---

## 10. Practical exercises (تمرین‌های عملی)

1. دستور `.venv/bin/pyats version check` را در ترمینال اجرا کنید و لیست پکیج‌های رسمی نصب‌شده (`pyats.aetest`, `pyats.topology`, `genie`, `unicon`) را بررسی کنید.
2. اسکریپت `aetest_health_check.py` را یک بار با `--scenario healthy` و یک بار با `--scenario unhealthy` اجرا کنید و جدول `SUMMARY` پایان خروجی pyATS را مقایسه کنید.

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

- در اجرای `--scenario healthy`، هر ۵ بخش (`CommonSetup`, سه `Testcase`, و `CommonCleanup`) وضعیت **`PASSED`** دریافت می‌کنند و نرخ موفقیت **`100.0%`** نمایش داده می‌شود.
- در اجرای `--scenario unhealthy`، بخش‌های `InterfaceHealthTestcase` و `RoutingTableTestcase` وضعیت **`FAILED`** دریافت می‌کنند و دلیل دقیق هر خطا در لاگ چاپ می‌شود.

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** تفاوت بین **Library** و **Framework** در اکوسیستم pyATS چیست؟ (`Genie` کدام است و `AEtest` کدام است؟)
2. **سؤال ۲:** سه جزء اصلی اکوسیستم pyATS (`pyATS Core`, `Genie`, `Unicon`) هر کدام چه مسئولیتی دارند؟
3. **سؤال ۳:** تفاوت وضعیت `Failed` و `Errored` در گزارش‌های pyATS چیست؟
4. **سؤال ۴:** چرا عملیات بستن اتصال دستگاه و ذخیره گزارش نهایی باید در `CommonCleanup` قرار بگیرد؟

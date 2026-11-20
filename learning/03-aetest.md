<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۲ (بخش دوم): کالبدشکافی عمیق AEtest در pyATS (`03-aetest.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

**`pyats.aetest` (Automated Execution Test)** موتور ساختاردهی و اجرای تست در فریم‌ورک **Cisco pyATS** است. اگر در توسعه **Android / Kotlin** با **JUnit 5** کار کرده باشید، می‌توانید ساختار `AEtest` را به صورت زیر مقایسه کنید:

| مفهوم در `pyats.aetest` | معادل در `JUnit 5 (Kotlin)` | نقش در چرخه حیات تست |
| :--- | :--- | :--- |
| `class CommonSetup(aetest.CommonSetup)` | `@BeforeAll` (در سطح کل Suite) | آماده‌سازی اولیه پیش از اجرای تمام `Testcase`ها. |
| `@aetest.subsection` | متدهای مرحله‌ای داخل `@BeforeAll` / `@AfterAll` | تقسیم `CommonSetup` و `CommonCleanup` به گام‌های کوچک و قابل ردیابی. |
| `class MyTest(aetest.Testcase)` | کلاس تست JUnit | یک واحد تست مستقل با هدف مشخص (مثلاً تست اینترفیس‌ها). |
| `@aetest.setup` | `@BeforeEach` | پیش‌نیاز اختصاصی یک `Testcase` قبل از متدهای `@aetest.test` همان کلاس. |
| `@aetest.test` | `@Test` | متد اصلی اعتبارسنجی که نتیجه `passed` یا `failed` تولید می‌کند. |
| `@aetest.cleanup` | `@AfterEach` | پاک‌سازی اختصاصی یک `Testcase`. |
| `class CommonCleanup(aetest.CommonCleanup)` | `@AfterAll` | پاک‌سازی نهایی، بستن اتصالات و تولید گزارش در پایان کل اسکریپت. |

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

در تست‌های شبکه، برخلاف تست‌های واحد ساده، ترتیب مراحل و وابستگی بین داده‌ها اهمیت حیاتی دارد:
1. ابتدا باید فایل پیکربندی (`expected_health_policy.yaml`) و توپولوژی (`devices.yaml.example`) بارگذاری شوند.
2. سپس باید یک بار از روتر Snapshot وضعیت گرفته شود تا برای هر تست بارها دستورات تکراری روی روتر اجرا نشود.
3. اگر روتر کلاً در دسترس نباشد (`reachable == False`)، تست‌های اینترفیس و مسیریابی باید به صورت هوشمند `SKIPPED` شوند، نه اینکه با خطای `KeyError` کرش کنند.
4. سیستم تزریق پارامتر (`Parameter Driven Testing`) در `AEtest` این اشتراک داده بین بخش‌ها را بدون متغیرهای Global خطرناک فراهم می‌کند.

---

## 3. How does it work? (چطور کار می‌کند؟)

### مکانیزم Parameter Injection در AEtest
در `AEtest`، هر بخش (`Section`) در یک درخت سلسله‌مراتبی قرار دارد:
- ریشه درخت، شیء `TestScript` است (`self.parent` در داخل `CommonSetup`, `Testcase`, و `CommonCleanup`).
- دیکشنری `self.parent.parameters` فضای اشتراک پارامترها در سطح کل اسکریپت است.
- وقتی در `CommonSetup` می‌نویسیم:
  ```python
  self.parent.parameters["snapshot"] = snapshot
  self.parent.parameters["policy"] = policy
  ```
  موتور `AEtest` به صورت خودکار (مشابه **Dependency Injection** در `Hilt / Koin`) هر متدی در `Testcase`ها که آرگومان‌هایی هم‌نام با کلیدهای `parameters` (`snapshot: DeviceSnapshot, policy: ExpectedDeviceHealthPolicy`) داشته باشد را شناسایی کرده و مقادیر را به آن تزریق می‌کند!

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **TestScript:** کل فایل پایتون حاوی کلاس‌های `CommonSetup`, `Testcase`, و `CommonCleanup`.
- **Container Section:** بخش‌هایی که خود شامل زیربخش هستند (`CommonSetup`, `Testcase`, `CommonCleanup`).
- **Leaf Section:** متدهایی که با دکوراتورهای `@aetest.subsection`, `@aetest.setup`, `@aetest.test`, `@aetest.cleanup` علامت‌گذاری شده‌اند.
- **Result APIs:** متدهای داخلی هر بخش برای اعلام صریح نتیجه:
  - `self.passed("message")`
  - `self.failed("message")`
  - `self.skipped("message")`
  - `self.errored("message")`

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`src/network_health/tests/aetest_health_check.py`**: پیاده‌سازی کامل اسکریپت `AEtest` پروژه.
- **`src/network_health/tests/health_check_job.py`**: فایل Job برای اجرای `aetest_health_check.py` تحت موتور `Easypy`.

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی در `aetest_health_check.py`)

1. **`CommonSetup.load_policy_and_testbed`**:
   فایل YAML سیاست سلامت و فایل Testbed را بارگذاری کرده و در `self.parent.parameters` ذخیره می‌کند.
2. **`CommonSetup.connect_and_collect_snapshot`**:
   بسته به پارامتر `scenario` (`healthy`, `unhealthy`, `unreachable`)، شیء `SimulatedIosXeDevice` را ساخته، خروجی دستورات را با **Genie** پارس کرده و `snapshot` را در `self.parent.parameters["snapshot"]` قرار می‌دهد.
3. **`DeviceAvailabilityTestcase`**:
   با فراخوانی `validate_device_availability(snapshot, policy)` بررسی می‌کند آیا روتر در دسترس است و نام آن (`hostname`) تطابق دارد یا خیر.
4. **`InterfaceHealthTestcase`**:
   - در `@aetest.setup` (`check_interfaces_present`) بررسی می‌کند که اگر `not snapshot.reachable` بود، کل این Testcase را با `self.skipped(...)` رد کند.
   - در `@aetest.test` اول وضعیت `admin_status` و `oper_status` تمام اینترفیس‌ها را بررسی می‌کند.
   - در `@aetest.test` دوم آدرس IPv4 و Prefix Length تمام اینترفیس‌ها را اعتبارسنجی می‌کند.
5. **`RoutingTableTestcase`**:
   مسیرهای جدول مسیریابی (`0.0.0.0/0`, `10.10.20.0/24`, `172.16.10.0/24`) را بررسی می‌کند.
6. **`CommonCleanup.generate_reports_and_disconnect`**:
   گزارش‌های JSON و Markdown را در پوشه `reports/` ذخیره کرده و متد `connector.disconnect()` را فراخوانی می‌کند.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام اجرا در `aetest_health_check.py`)

1. کاربر دستور `python src/network_health/tests/aetest_health_check.py --scenario healthy` را اجرا می‌کند.
2. تابع `parse_cli_args()` آرگومان‌های خط فرمان را می‌خواند و به `aetest.main(scenario=...)` پاس می‌دهد.
3. موتور `AEtest` آرگومان‌های ورودی `aetest.main()` را در `parameters` ریشه قرار می‌دهد.
4. `CommonSetup` اجرا می‌شود و اشیاء `policy`, `testbed`, `connector`, و `snapshot` را می‌سازد.
5. سه کلاس `Testcase` به ترتیب تعریف‌شده در فایل اجرا می‌شوند و پارامترهای `snapshot` و `policy` به متدهای `@aetest.test` تزریق می‌گردند.
6. `CommonCleanup` اجرا شده، فایل‌های `reports/health_report_<scenario>.json` و `.md` را تولید می‌کند.
7. موتور `AEtest` جدول خلاصه نتایج (`Section Results Summary`) را در ترمینال چاپ کرده و کد خروجی (`Exit Code 0` برای موفقیت و غیر صفر برای شکست) برمی‌گرداند.

---

## 8. Real code examples (مثال واقعی از کدهای پروژه)

```python
class InterfaceHealthTestcase(aetest.Testcase):
    """Testcase 2 & 3: Validate interface admin/operational status and IPv4 addressing."""

    @aetest.setup
    def check_interfaces_present(self, snapshot: DeviceSnapshot) -> None:
        if not snapshot.reachable:
            self.skipped("Skipping interface checks because device is unreachable.")

    @aetest.test
    def verify_interfaces_operational_status(
        self,
        snapshot: DeviceSnapshot,
        policy: ExpectedDeviceHealthPolicy,
    ) -> None:
        failures: list[str] = []
        for rule in policy.interfaces:
            result = validate_interface_status(snapshot, rule)
            if result.outcome != TestOutcome.PASS:
                failures.append(result.message)

        if failures:
            self.failed(" | ".join(failures))
        else:
            self.passed("All required interfaces are administratively and operationally UP.")
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **عدم تطابق نام آرگومان متد `@aetest.test` با کلید داخل `self.parent.parameters`:**
   - **نشانه:** خطای `TypeError: missing 1 required positional argument` در زمان اجرای تست.
   - **راه‌حل:** نام پارامتر در امضای متد (مثلاً `snapshot`) باید دقیقاً با کلیدی که در `self.parent.parameters["snapshot"]` ذخیره کرده‌اید یکسان باشد.
2. **فراخوانی `self.failed()` در اولین خطای حلقه بدون بررسی سایر اینترفیس‌ها:**
   - **نکته مهم:** در `AEtest`، فراخوانی `self.failed()` بلافاصله اجرای همان متد `@aetest.test` را متوقف می‌کند! به همین دلیل در کد بالا ابتدا تمام اینترفیس‌ها را در حلقه بررسی کرده، خطاها را در لیست `failures` جمع می‌کنیم و در انتهای حلقه یک بار `self.failed(" | ".join(failures))` را صدا می‌زنیم تا مهندس شبکه تمام اینترفیس‌های خراب را یکجا ببیند.

---

## 10. Practical exercises (تمرین‌های عملی)

### تمرین ۱: آزمایش سناریوی `unreachable` و مشاهده رفتار `@aetest.setup`
دستور زیر را اجرا کنید تا ببینید وقتی روتر در دسترس نیست، `DeviceAvailabilityTestcase` وضعیت `FAILED` می‌گیرد اما دو Testcase بعدی به صورت ایمن `SKIPPED` می‌شوند:
```bash
PYTHONPATH=src .venv/bin/python src/network_health/tests/aetest_health_check.py --scenario unreachable
```

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

در جدول خلاصه انتهای خروجی ترمینال مشاهده خواهید کرد:
- `common_setup`: **`PASSED`**
- `DeviceAvailabilityTestcase`: **`FAILED`** (`Device 'sim-rtr-core-01' is unreachable.`)
- `InterfaceHealthTestcase`: **`SKIPPED`** (`Skipping interface checks because device is unreachable.`)
- `RoutingTableTestcase`: **`SKIPPED`** (`Skipping routing table checks because device is unreachable.`)
- `common_cleanup`: **`PASSED`**

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** موتور `AEtest` چطور متوجه می‌شود که چه مقداری را باید به آرگومان `snapshot` در متد `verify_expected_routes(self, snapshot, policy)` پاس بدهد؟
2. **سؤال ۲:** چرا در متد `verify_interfaces_operational_status` به جای اینکه داخل حلقه `for` بلافاصله `self.failed()` را صدا بزنیم، ابتدا خطاها را در لیست `failures` جمع‌آوری می‌کنیم؟
3. **سؤال ۳:** تفاوت `@aetest.subsection` و `@aetest.test` چیست و هر کدام در کدام کلاس‌ها استفاده می‌شوند؟
4. **سؤال ۴:** در چه صورتی یک `Testcase` وضعیت `SKIPPED` به خود می‌گیرد؟

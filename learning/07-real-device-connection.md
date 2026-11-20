<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۵: اتصال به روتر واقعی سیسکو با Unicon و Cisco DevNet Sandbox (`07-real-device-connection.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

- **Cisco Unicon:** موتور اتصال رسمی در اکوسیستم **pyATS** است که ارتباط با تجهیزات شبکه از طریق پروتکل‌های **SSH** و **Telnet** را مدیریت می‌کند. برخلاف کتابخانه‌های ساده SSH (مثل `Paramiko` خام)، **Unicon** یک **State Machine** هوشمند برای خط فرمان روتر دارد؛ یعنی خودش متوجه می‌شود روتر الان در حالت `User Exec (> )`، `Privileged Exec (# )` یا `Config Mode ((config)# )` است، صفحه‌بندی (`--More--`) را خودکار مدیریت می‌کند و Promptهای غیرمنتظره را تشخیص می‌دهد.
- **Cisco DevNet Sandbox:** آزمایشگاه ابری و رایگان شرکت سیسکو (`devnetsandbox.cisco.com`) که به توسعه‌دهندگان اجازه می‌دهد یک روتر واقعی مجازی‌شده (مانند **Catalyst 8000V / CSR1000v** با سیستم‌عامل **IOS-XE**) رزرو کنند و با SSH واقعی به آن متصل شوند.

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

شبیه‌ساز آفلاین (`SimulatedIosXeDevice`) برای توسعه سریع و تست‌های CI/CD عالی است، اما در نهایت سیستم ما باید بتواند بدون تغییر در کدهای `core/` و `validators.py`، به یک روتر واقعی سیسکو متصل شود، دستورات `show interfaces` و `show ip route` را از طریق SSH اجرا کند و سلامت شبکه واقعی را بسنجد.

---

## 3. How does it work? (چطور کار می‌کند؟)

1. اطلاعات اتصال (IP، پورت، نام کاربری و رمز عبور) در متغیرهای محیطی سیستم‌عامل (`CISCO_SANDBOX_HOST`, `CISCO_SANDBOX_PORT`, `CISCO_SANDBOX_USERNAME`, `CISCO_SANDBOX_PASSWORD`) قرار می‌گیرند.
2. فایل [testbed/devices.yaml.example](file:///Users/hesam/.gemini/antigravity/scratch/network-health-check/testbed/devices.yaml.example) با سینتکس `"%ENV{VAR_NAME}"` این مقادیر را در زمان اجرا جایگزین می‌کند (هیچ رمزی در کد یا گیت ذخیره نمی‌شود).
3. کلاس `PyAtsRealDeviceConnector` در [src/network_health/devices/real_device.py](file:///Users/hesam/.gemini/antigravity/scratch/network-health-check/src/network_health/devices/real_device.py) ابتدا با تابع `validate_real_device_env_vars()` بررسی می‌کند که متغیرهای محیطی واقعی ست شده باشند.
4. با `device.connect()` یک نشست SSH از طریق `unicon.Unicon` باز می‌کند.
5. با `device.parse("show interfaces")` و `device.parse("show ip route")`، کتابخانه **Genie** دستور را مستقیماً روی نشست SSH اجرا کرده و خروجی پارس‌شده را به `extract_interfaces_from_genie` و `extract_routes_from_genie` می‌دهد.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم + نکات مصاحبه فنی)

- **Unicon State Machine:** مدیریت خودکار وضعیت‌های CLI روتر (`enable`, `config`, `exec`) و هندل کردن `terminal length 0` (غیرفعال کردن صفحه‌بندی خروجی روتر).
- **Secret Injection via `%ENV{...}`:** استاندارد امنیتی pyATS برای جلوگیری از Hardcode کردن رمزهای عبور در فایل‌های YAML.
- **Liskov Substitution Principle (LSP):** هم `SimulatedIosXeDevice` و هم `PyAtsRealDeviceConnector` از `NetworkDeviceConnector` ارث‌بری می‌کنند؛ بنابراین لایه تست و API بدون تغییر کد می‌تواند بین حالت آفلاین و روتر واقعی سوییچ کند.

> **💡 نکته طلایی مصاحبه فنی:**
> اگر در مصاحبه پرسیدند: *«چرا در اتوماسیون شبکه به جای `Paramiko` خام از `Unicon` یا `Netmiko` استفاده می‌کنیم؟»*
> پاسخ دهید: «چون ارتباط با روتر از طریق SSH یک Interactive Shell است نه یک RPC ساده. روترها خروجی طولانی را با `--More--` صفحه‌بندی می‌کنند، Promptهای متفاوتی در مدهای مختلف دارند و گاهی پیام‌های لاگ وسط خروجی چاپ می‌کنند. `Unicon` یک State Machine کامل دارد که به صورت خودکار `terminal length 0` می‌زند، Prompt را تشخیص می‌دهد و تایم‌اوت‌ها را مدیریت می‌کند.»

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`src/network_health/devices/real_device.py`**: پیاده‌سازی کامل `PyAtsRealDeviceConnector` و تابع امنیتی `validate_real_device_env_vars`.
- **`testbed/devices.yaml.example`**: فایل پیکربندی Testbed با درایور `unicon.Unicon` و پروتکل `ssh`.
- **`.env.example`**: الگوی متغیرهای محیطی برای اتصال به Cisco DevNet Sandbox.

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی)

- **`validate_real_device_env_vars()`**: بررسی می‌کند که هر ۴ متغیر محیطی Sandbox مقداردهی شده باشند و مقدار پیش‌فرض (`replace_with_...`) نباشند؛ در غیر این صورت `ConfigurationError` پرتاب می‌کند.
- **`PyAtsRealDeviceConnector.connect()`**: فایل Testbed را بارگذاری کرده و متد `device.connect(learn_hostname=True, connection_timeout=...)` را صدا می‌زند.
- **`PyAtsRealDeviceConnector.collect_snapshot()`**: دستورات `show interfaces` و `show ip route` را با `self._pyats_device.parse(...)` به صورت زنده روی روتر اجرا و پارس کرده و یک `DeviceSnapshot(is_Simulated=False)` برمی‌گرداند.

---

## 7. Step-by-step execution flow (راهنمای گام‌به‌گام دریافت دسترسی Cisco DevNet Sandbox و اتصال)

1. به سایت [Cisco DevNet Sandbox Catalog](https://devnetsandbox.cisco.com) بروید و با اکانت رایگان GitHub یا Google وارد شوید.
2. یک آزمایشگاه **Cisco Modeling Labs (CML)** یا **Catalyst 8000V / IOS-XE Always-On** انتخاب کنید.
3. متغیرهای محیطی را در ترمینال خود ست کنید:
   ```bash
   export CISCO_SANDBOX_HOST="sandbox-iosxe-latest-1.cisco.com"
   export CISCO_SANDBOX_PORT="22"
   export CISCO_SANDBOX_USERNAME="your_sandbox_username"
   export CISCO_SANDBOX_PASSWORD="your_sandbox_password"
   ```
4. از طریق `PyAtsRealDeviceConnector` به روتر متصل شوید و Snapshot واقعی بگیرید.

---

## 8. Real code examples (مثال واقعی استفاده از `PyAtsRealDeviceConnector`)

```python
from network_health.devices.real_device import PyAtsRealDeviceConnector

connector = PyAtsRealDeviceConnector(
    hostname="sim-rtr-core-01",
    testbed_path="testbed/devices.yaml.example",
    connection_timeout_seconds=30,
)
connector.connect()
snapshot = connector.collect_snapshot()
connector.disconnect()

print("Is Simulated:", snapshot.is_Simulated)  # False
print("Reachable:", snapshot.reachable)        # True
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **عدم تطابق Hostname واقعی روتر با نام تعریف‌شده در Testbed:**
   - **راه‌حل:** پاس دادن `learn_hostname=True` به `device.connect()` در Unicon (همان‌طور که در خط ۱۰۱ فایل `real_device.py` انجام دادیم) باعث می‌شود Unicon به طور خودکار نام واقعی روتر را از روی Prompt یاد بگیرد و خطای Timeout ندهد.
2. **ذخیره کردن رمز عبور روتر داخل فایل `devices.yaml` و کامیت در Git:**
   - **راه‌حل:** همیشه از `"%ENV{CISCO_SANDBOX_PASSWORD}"` استفاده کنید و `testbed/devices.yaml` شخصی را در `.gitignore` نگه دارید.

---

## 10. Practical exercises (تمرین‌های عملی)

تست واحد مربوط به اعتبارسنجی امنیتی اتصال واقعی را اجرا کنید تا ببینید سیستم چگونه جلوی اتصال با رمز عبور خالی یا Placeholder را می‌گیرد:
```bash
.venv/bin/pytest src/network_health/tests/test_advanced_phases.py -k "real_device"
```

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

تست `test_real_device_connector_rejects_missing_or_placeholder_credentials` با وضعیت **`PASSED`** اجرا می‌شود و تأیید می‌کند که بدون ست کردن متغیرهای محیطی معتبر، استثنای `ConfigurationError` پرتاب می‌شود.

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** پارامتر `learn_hostname=True` در متد `device.connect()` کتابخانه Unicon چه مشکلی را حل می‌کند؟
2. **سؤال ۲:** تفاوت فراخوانی `device.parse("show interfaces")` در `PyAtsRealDeviceConnector` با `device.parse("show interfaces", output=raw_text)` در شبیه‌ساز آفلاین چیست؟

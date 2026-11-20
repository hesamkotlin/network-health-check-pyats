<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۲ (بخش سوم): توپولوژی، Testbed و دستگاه‌ها در pyATS (`04-testbed-and-devices.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

در **Cisco pyATS**، مفهوم **Testbed** نمایش شیءگرای محیط شبکه شماست. فایل **Testbed YAML** شناسنامه فنی شبکه است که مشخص می‌کند:
- چه دستگاه‌هایی (`Devices`: روترها، سوییچ‌ها، فایروال‌ها) در شبکه وجود دارند.
- هر دستگاه چه سیستم‌عاملی (`os: iosxe`, `nxos`, `iosxr`) و چه نقشی (`type: router`) دارد.
- چطور باید به هر دستگاه متصل شد (`connections: ssh / unicon`).
- اطلاعات احراز هویت (`credentials`) از کجا خوانده می‌شوند.
- اینترفیس‌ها و لینک‌های ارتباطی بین دستگاه‌ها (`topology`) چگونه تعریف شده‌اند.

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

یکی از قوانین طلایی معماری نرم‌افزار (که در اندروید هم رعایت می‌کنید) **جدا کردن پیکربندی محیط از کد منبع (`Separation of Configuration from Code`)** است.
- ما هرگز آدرس IP روتر، پورت SSH، نام کاربری یا رمز عبور را داخل کدهای Python هاردکد نمی‌کنیم.
- با داشتن فایل استاندارد `testbed/devices.yaml.example`، کد تست ما می‌تواند ساختار توپولوژی دستگاه `sim-rtr-core-01` را از طریق `pyats.topology.loader.load()` بارگذاری و اعتبارسنجی کند و در فاز ۵ بدون تغییر ساختار تست، به روتر واقعی **Cisco DevNet Sandbox** متصل شود.

---

## 3. How does it work? (چطور کار می‌کند؟)

وقتی دستور `testbed = topology_loader.load("testbed/devices.yaml.example")` اجرا می‌شود:
1. ماژول `pyats.topology.loader` فایل YAML را پارس می‌کند.
2. عبارات پویا مانند `"%ENV{CISCO_SANDBOX_HOST}"` را با مقادیر متغیرهای محیطی سیستم‌عامل (`os.environ`) جایگزین می‌کند.
3. یک شیء `Testbed` می‌سازد که حاوی دیکشنری `testbed.devices` است.
4. هر عضو در `testbed.devices["sim-rtr-core-01"]` یک شیء `Device` است که خود حاوی اشیاء `Interface` در `device.interfaces` می‌باشد.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **`Testbed` Object:** شیء ریشه توپولوژی که کل شبکه تحت تست را نمایندگی می‌کند.
- **`Device` Object:** نماینده یک روتر یا سوییچ در pyATS (`device.name`, `device.os`, `device.type`, `device.interfaces`).
- **`Interface` Object:** نماینده یک پورت شبکه روی دستگاه (`interface.name`, `interface.ipv4`, `interface.type`).
- **`%ENV{VAR_NAME}` Markup:** سینتکس رسمی pyATS در فایل‌های YAML برای خواندن امن اطلاعات حساس (مانند رمز عبور) از متغیرهای محیطی بدون ذخیره آن‌ها در فایل YAML.
- **`NetworkDeviceConnector` (`devices/base.py`)**: کلاس انتزاعی (`ABC`) معماری ما که بین منطق تست و جزئیات دستگاه (`SimulatedIosXeDevice` در فاز ۳ و روتر واقعی در فاز ۵) یک مرز تمیز ایجاد می‌کند.

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`testbed/devices.yaml.example`**: فایل استاندارد Testbed پروژه شامل تعریف دستگاه `sim-rtr-core-01`، بلوک `connections`، بلوک `credentials` با `%ENV{...}`، و بلوک `topology` (شامل `GigabitEthernet1`, `GigabitEthernet2`, `Loopback0`).
- **`.env.example`**: الگوی متغیرهای محیطی مورد استفاده توسط فایل Testbed.
- **`src/network_health/devices/base.py`**: رابط انتزاعی `NetworkDeviceConnector`.

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی)

- **`pyats.topology.loader.load(path)`**: تابع رسمی pyATS برای تبدیل فایل YAML به درخت اشیاء `Testbed -> Device -> Interface`.
- **`NetworkDeviceConnector` (`src/network_health/devices/base.py`)**:
  متدهای قراردادی زیر را اجباری (`@abstractmethod`) می‌کند:
  - `hostname -> str`
  - `os_type -> str`
  - `is_simulated -> bool`
  - `connect() -> None`
  - `disconnect() -> None`
  - `execute_command(command: str) -> str`
  - `collect_snapshot() -> DeviceSnapshot`

---

## 7. Step-by-step execution flow (روند گام‌به‌گام بارگذاری Testbed)

1. در بخش `CommonSetup.load_policy_and_testbed` (`aetest_health_check.py`)، متغیرهای محیطی پیش‌فرض برای اجرای آفلاین تنظیم می‌شوند تا `%ENV{...}` خطا ندهد.
2. تابع `topology_loader.load(str(testbed_path))` فراخوانی می‌شود.
3. بررسی می‌شود که آیا `policy.hostname` (`sim-rtr-core-01`) در `testbed.devices` وجود دارد یا خیر.
4. شیء `testbed` در `self.parent.parameters["testbed"]` ذخیره می‌شود.

---

## 8. Real code examples (مثال واقعی بارگذاری و بازرسی Testbed با Python)

```python
import os
from pyats.topology import loader

os.environ.setdefault("CISCO_SANDBOX_HOST", "127.0.0.1")
os.environ.setdefault("CISCO_SANDBOX_PORT", "22")
os.environ.setdefault("CISCO_SANDBOX_USERNAME", "offline_user")
os.environ.setdefault("CISCO_SANDBOX_PASSWORD", "offline_pass")

testbed = loader.load("testbed/devices.yaml.example")
device = testbed.devices["sim-rtr-core-01"]

print("Device Name:", device.name)
print("Device OS:", device.os)
for iface_name, iface_obj in device.interfaces.items():
    print(f"Interface: {iface_name} | IPv4: {iface_obj.ipv4}")
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **عدم تعریف متغیر محیطی استفاده شده در `%ENV{...}` قبل از `loader.load()`:**
   - **نشانه:** اگر متغیر محیطی تعریف نشده باشد، رشته خام یا مقدار خالی جایگزین می‌شود و در صورت نیاز به عدد (مثل `port`) خطای اعتبارسنجی اسکیما (`YAML Schema Error`) رخ می‌دهد.
   - **راه‌حل:** همیشه قبل از بارگذاری Testbed مطمئن شوید متغیرهای محیطی تنظیم شده‌اند.
2. **فراموش کردن فیلد الزامی `os` در تعریف دستگاه داخل `devices.yaml`:**
   - کتابخانه‌های `Genie` و `Unicon` برای انتخاب Parser و درایور CLI دقیقاً به فیلد `os: iosxe` وابسته هستند.

---

## 10. Practical exercises (تمرین‌های عملی)

دستور زیر را در ترمینال اجرا کنید تا فایل `testbed/devices.yaml.example` را با `pyats.topology.loader` بارگذاری کرده و اینترفیس‌های تعریف‌شده در توپولوژی را چاپ کنید:

```bash
PYTHONPATH=src .venv/bin/python -c "
import os
from pyats.topology import loader
for k, v in [('CISCO_SANDBOX_HOST','127.0.0.1'),('CISCO_SANDBOX_PORT','22'),('CISCO_SANDBOX_USERNAME','u'),('CISCO_SANDBOX_PASSWORD','p')]:
    os.environ[k] = v
tb = loader.load('testbed/devices.yaml.example')
dev = tb.devices['sim-rtr-core-01']
print('Testbed:', tb.name, '| Device:', dev.name, '| OS:', dev.os)
for name, iface in dev.interfaces.items():
    print(' -', name, '->', iface.ipv4)
"
```

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

```text
Testbed: network_health_check_testbed | Device: sim-rtr-core-01 | OS: iosxe
 - GigabitEthernet1 -> 10.10.20.1/24
 - GigabitEthernet2 -> 172.16.10.1/24
 - Loopback0 -> 192.168.255.1/32
```

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** کاربرد عبارت `"%ENV{CISCO_SANDBOX_PASSWORD}"` در فایل `testbed/devices.yaml.example` چیست و کدام قانون امنیتی پروژه را محقق می‌کند؟
2. **سؤال ۲:** تفاوت بخش `devices` و بخش `topology` در فایل YAML تست‌بد pyATS چیست؟
3. **سؤال ۳:** چرا کلاس `NetworkDeviceConnector` را به صورت یک `ABC` (کلاس پایه انتزاعی) طراحی کردیم؟
4. **سؤال ۴:** چرا فیلد `os: iosxe` در تعریف دستگاه در Testbed اجباری و حیاتی است؟

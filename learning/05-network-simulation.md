<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۳: شبیه‌سازی آفلاین شبکه (`05-network-simulation.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

**Offline Network Simulation** در مهندسی اتوماسیون شبکه به معنای ایجاد یک لایه شبیه‌ساز قطعی (`Deterministic Simulator` / `Fake Data Source`) است که خروجی‌های واقعی دستورات CLI سیستم‌عامل شبکه (مانند **Cisco IOS-XE**) را بدون نیاز به روتر فیزیکی یا اتصال شبکه بازتولید می‌کند.

در معماری **Android / Kotlin (Clean Architecture)**، این لایه دقیقاً معادل **`FakeNetworkDataSource`** است که فایل‌های JSON نمونه (`Fixtures`) را می‌خواند تا بتوانید `UseCase`ها و `ViewModel`ها را ۱۰۰٪ آفلاین، سریع و قابل تکرار تست کنید.

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

1. **اجرای ۱۰۰٪ آفلاین:** شما برای یادگیری و اجرای تست‌های **pyATS** و **Genie** نیازی به خرید روتر سیسکو، اجرای ماشین‌های مجازی سنگین یا اتصال دائمی به اینترنت ندارید.
2. **تولید سناریوهای شکست قابل‌پیش‌بینی (`Deterministic FAIL Scenarios`):** در یک روتر واقعی اشتراکی (مثل Sandbox)، شما همیشه اجازه ندارید یک اینترفیس اصلی را `shutdown` کنید یا جدول مسیریابی را خراب کنید تا ببینید تست شما چگونه خطا را تشخیص می‌دهد. اما در شبیه‌ساز آفلاین، ما هر سه سناریوی `HEALTHY`, `UNHEALTHY` و `UNREACHABLE` را با دقت ۱۰۰٪ شبیه‌سازی می‌کنیم.
3. **صداقت معماری (قانون ۶ و ۷ پروژه):** شبیه‌ساز ما هرگز ادعا نمی‌کند یک اتصال واقعی SSH به روتر است؛ ویژگی `is_simulated` همیشه برابر `True` است و در تمام گزارش‌ها عبارت `Offline Simulation (Simulated Device)` درج می‌شود.

---

## 3. How does it work? (چطور کار می‌کند؟)

1. کلاس `SimulatedIosXeDevice` از رابط انتزاعی `NetworkDeviceConnector` ارث‌بری می‌کند.
2. هنگام ساخت نمونه (`__init__`)، یک سناریو از نوع `SimulationScenario` (`HEALTHY`, `UNHEALTHY`, `UNREACHABLE`) دریافت می‌کند.
3. در متد `connect()`:
   - اگر سناریو `UNREACHABLE` باشد، استثنای `DeviceConnectionError` پرتاب می‌کند.
   - در غیر این صورت، فایل Fixture متناظر (`test_data/iosxe_healthy_outputs.json` یا `test_data/iosxe_unhealthy_outputs.json`) را بارگذاری می‌کند.
4. در متد `execute_command(command)`، خروجی متنی دقیق دستور Cisco IOS-XE (`show interfaces`, `show ip route`, `show ip interface brief`) را از دیکشنری بارگذاری‌شده برمی‌گرداند.
5. در متد `collect_snapshot()`، این متن‌های CLI را به **Parserهای واقعی Cisco Genie** می‌دهد تا به مدل دامنه `DeviceSnapshot` تبدیل شوند.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **Test Fixture:** داده‌های ورودی ثابت و شناخته‌شده (فایل‌های JSON در پوشه `test_data/`) که خروجی تست روی آن‌ها کاملاً قابل پیش‌بینی است.
- **Configuration Drift:** حالتی که پیکربندی فعلی روتر نسبت به وضعیت استاندارد مورد انتظار تغییر کرده است (مثلاً تغییر ناخواسته IP اینترفیس `GigabitEthernet1` به `10.10.99.1/24` در سناریوی `UNHEALTHY`).
- **Administratively Down:** وضعیتی در روترهای Cisco که مهندس شبکه دستور `shutdown` را روی اینترفیس اجرا کرده است (مانند `GigabitEthernet2` در سناریوی `UNHEALTHY`).

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`src/network_health/simulation/simulated_device.py`**: پیاده‌سازی کلاس `SimulatedIosXeDevice` و Enum مربوط به `SimulationScenario`.
- **`test_data/iosxe_healthy_outputs.json`**: خروجی‌های استاندارد دستورات CLI روتر در حالت سالم (`PASS`).
- **`test_data/iosxe_unhealthy_outputs.json`**: خروجی‌های دستورات CLI روتر در حالت معیوب (`FAIL`) شامل ۳ مشکل عمدی:
  1. تغییر IP اینترفیس `GigabitEthernet1` از `10.10.20.1/24` به `10.10.99.1/24` (که باعث تغییر زیرشبکه متصل `10.10.20.0/24` به `10.10.99.0/24` در جدول مسیریابی نیز می‌شود).
  2. خاموش بودن (`administratively down`) اینترفیس `GigabitEthernet2`.
  3. حذف شدن مسیر پیش‌فرض (`0.0.0.0/0` یا `Gateway of last resort`) از جدول مسیریابی.

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی)

- **`SimulationScenario(str, Enum)`**: سه حالت `HEALTHY`, `UNHEALTHY`, `UNREACHABLE` را تعریف می‌کند.
- **`SimulatedIosXeDevice.connect()`**: فایل JSON مربوط به سناریو را خوانده و صحت ساختار آن را بررسی می‌کند.
- **`SimulatedIosXeDevice.execute_command(command)`**: اجرای دستور CLI روی روتر شبیه‌سازی‌شده را تقلید می‌کند و اگر دستور در Fixture تعریف نشده باشد، استثنای صریح `CommandExecutionError` پرتاب می‌کند.
- **`SimulatedIosXeDevice.collect_snapshot()`**: زنجیره کامل `execute_command` -> `parse_cli_with_genie` -> `extract_interfaces_from_genie` / `extract_routes_from_genie` -> `DeviceSnapshot` را اجرا می‌کند.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام اجرا در شبیه‌ساز)

```text
SimulatedIosXeDevice(scenario=SimulationScenario.UNHEALTHY)
  │
  ├─► 1. connect()
  │      Loads `test_data/iosxe_unhealthy_outputs.json`
  │
  └─► 2. collect_snapshot()
         ├─► execute_command("show interfaces") -> raw CLI text
         ├─► execute_command("show ip route")   -> raw CLI text
         ├─► parse_cli_with_genie(...)          -> Genie structured dict
         └─► returns DeviceSnapshot(is_Simulated=True, reachable=True, ...)
```

---

## 8. Real code examples (مثال واقعی استفاده از شبیه‌ساز)

```python
from network_health.simulation.simulated_device import (
    SimulatedIosXeDevice,
    SimulationScenario,
)

sim_router = SimulatedIosXeDevice(
    hostname="sim-rtr-core-01",
    scenario=SimulationScenario.HEALTHY,
)
sim_router.connect()
print(sim_router.execute_command("show ip interface brief"))
snapshot = sim_router.collect_snapshot()
sim_router.disconnect()

print("Is Simulated:", snapshot.is_Simulated)
print("Interfaces:", list(snapshot.interfaces.keys()))
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **فراخوانی `execute_command` قبل از `connect()`:**
   - باعث پرتاب استثنای `DeviceConnectionError` می‌شود. همیشه چرخه `connect()` -> `execute/collect` -> `disconnect()` را رعایت کنید.
2. **دستکاری نادرست فاصله‌ها و فرمت خروجی CLI در فایل‌های JSON Fixture:**
   - از آنجا که ما از **Parserهای واقعی Cisco Genie** استفاده می‌کنیم (نه یک Regex ساده دستی)، متن داخل `iosxe_healthy_outputs.json` باید دقیقاً فرمت خروجی واقعی Cisco IOS-XE را داشته باشد، وگرنه Genie استثنای `SchemaEmptyParserError` می‌دهد.

---

## 10. Practical exercises (تمرین‌های عملی)

با اجرای اسکریپت CLI زیر هر دو سناریوی `healthy` و `unhealthy` را اجرا کرده و خروجی جدول Markdown را مقایسه کنید:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_offline_checks.py --scenario healthy
PYTHONPATH=src .venv/bin/python scripts/run_offline_checks.py --scenario unhealthy
```

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

- دستور اول کد خروجی `0` و نتیجه **`Overall Outcome: PASS`** (`10 PASSED / 0 FAILED`) چاپ می‌کند.
- دستور دوم کد خروجی `1` و نتیجه **`Overall Outcome: FAIL`** (`5 PASSED / 5 FAILED`) چاپ می‌کند و دقیقاً ۵ مورد زیر را `FAIL` اعلام می‌کند:
  1. `interface_ip[GigabitEthernet1]` (تغییر IP به `10.10.99.1/24`)
  2. `interface_status[GigabitEthernet2]` (وضعیت `admin=down, oper=down`)
  3. `route[0.0.0.0/0]` (حذف مسیر پیش‌فرض)
  4. `route[10.10.20.0/24]` (حذف مسیر متصل به دلیل تغییر زیرشبکه `GigabitEthernet1`)
  5. `route[172.16.10.0/24]` (حذف مسیر متصل به دلیل خاموش بودن `GigabitEthernet2`)

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** چرا در `DeviceSnapshot` و `HealthCheckReport` فیلد `is_simulated` وجود دارد؟
2. **سؤال ۲:** در سناریوی `UNHEALTHY`، چرا تغییر IP اینترفیس `GigabitEthernet1` به `10.10.99.1/24` باعث شکست هم‌زمان دو تست (`interface_ip[GigabitEthernet1]` و `route[10.10.20.0/24]`) می‌شود؟
3. **سؤال ۳:** اگر متد `collect_snapshot()` روی یک دستگاه با سناریوی `UNREACHABLE` صدا زده شود چه مقداری برمی‌گرداند؟
4. **سؤال ۴:** معادل کلاس `SimulatedIosXeDevice` در معماری لایه‌ای پروژه‌های Android/Kotlin چیست؟

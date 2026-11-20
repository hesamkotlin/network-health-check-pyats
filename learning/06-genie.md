<style>
body, .markdown-body { direction: rtl; text-align: right; line-height: 1.85; }
h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, th, td { direction: rtl; text-align: right; }
pre, pre code { direction: ltr !important; text-align: left !important; unicode-bidi: embed; }
code { direction: ltr; unicode-bidi: isolate; }
</style>

# فاز ۴: تست شبکه و پارس کردن خروجی CLI با Cisco Genie (`06-genie.md`)

---

## 1. What is this technology? (این تکنولوژی چیست؟)

**Cisco Genie** کتابخانه استاندارد مدل‌سازی و پارس کردن دستورات شبکه در اکوسیستم **pyATS** است (`pip install "pyats[library]"`).

روترها و سوییچ‌ها در پاسخ به دستورات CLI مثل `show interfaces` یا `show ip route`، متن خام غیرساختاریافته (`Unstructured Human-Readable Text`) برمی‌گردانند. **Genie** بیش از ۳۰۰۰ **Parser** آماده و تست‌شده دارد که این متن‌های خام را به **دیکشنری‌های ساختاریافته و استاندارد Python (`Structured JSON/Dict Schema`)** تبدیل می‌کنند.

اگر بخواهیم با **Android / Kotlin** مقایسه کنیم:
- روتر شبکه مثل سروری است که به جای JSON، متن خام برمی‌گرداند.
- **Genie Parser** نقش **`Gson` / `Moshi` / `kotlinx.serialization`** را برای خروجی متنی خط فرمان روتر ایفا می‌کند!

---

## 2. Why do we need it in this project? (چرا در این پروژه به آن نیاز داریم؟)

نوشتن عبارات باقاعده (`Regex`) دستی برای پارس کردن خروجی دستورات سیسکو یکی از بزرگ‌ترین اشتباهات رایج در اتوماسیون شبکه است، زیرا خروجی دستورات پیچیده مثل `show ip route` حالت‌های بسیار متنوعی دارد.
با استفاده از **Genie**:
1. از Parserهای رسمی سیسکو برای `show interfaces` و `show ip route` روی پلتفرم `iosxe` استفاده می‌کنیم.
2. خروجی استاندارد دیکشنری Genie را دریافت کرده و سپس آن را به مدل‌های تایپ‌شده دامنه خودمان (`InterfaceState` و `RouteEntry`) نگاشت (`Map`) می‌کنیم.

---

## 3. How does it work? (چطور کار می‌کند؟)

### نحوه کارکرد Genie Parser در حالت آفلاین و آنلاین
1. در **Genie**، هر Parser به سیستم‌عامل شبکه (`os`) گره خورده است (مثلاً Parser دستور `show ip route` در `iosxe` با `nxos` متفاوت است).
2. برای اینکه Genie بداند کدام Parser را انتخاب کند، به یک شیء `genie.conf.base.Device` با ویژگی `os="iosxe"` نیاز دارد.
3. وقتی متد `genie_device.parse("show interfaces", output=raw_output)` را صدا می‌زنیم:
   - اگر آرگومان `output` پاس داده **نشود** (حالت آنلاین فاز ۵)، Genie خودش از طریق اتصال SSH دستور را روی روتر اجرا کرده و خروجی را پارس می‌کند.
   - اگر آرگومان `output=raw_output` پاس داده **شود** (حالت شبیه‌سازی آفلاین فاز ۳ و ۴)، Genie هیچ اتصال شبکه‌ای باز نمی‌کند و مستقیماً رشته متنی `raw_output` را با Parser رسمی `iosxe` پارس کرده و دیکشنری ساختاریافته برمی‌گرداند!

### محدودیت‌های مهم Parserهای Genie (که باید بدانید)
- **وابستگی به `os`:** باید حتماً `os="iosxe"` (یا پلتفرم صحیح) روی شیء `Device` و همچنین `device.custom.setdefault("abstraction", {})["order"] = ["os"]` تنظیم شود.
- **حساسیت به فرمت دقیق خروجی CLI:** اگر خروجی متنی با ساختار واقعی دستور سیسکو همخوانی نداشته باشد یا خالی باشد، Genie استثنای `SchemaEmptyParserError` پرتاب می‌کند.

---

## 4. Important concepts and terminology (مفاهیم و اصطلاحات مهم)

- **Genie Metaparser:** موتور اعتبارسنجی اسکیما در Genie که تضمین می‌کند خروجی هر Parser دقیقاً از یک ساختار دیکشنری استاندارد پیروی کند.
- **`SchemaEmptyParserError`:** استثنای رسمی Genie زمانی که متن ورودی با هیچ الگوی معتبری در Parser تطابق پیدا نکند.
- **VRF (Virtual Routing and Forwarding):** جدول مسیریابی مجازی در روتر. در خروجی Genie برای `show ip route`، مسیرهای اصلی زیر کلید `parsed["vrf"]["default"]["address_family"]["ipv4"]["routes"]` قرار می‌گیرند.

---

## 5. Explanation of each relevant source file (توضیح فایل‌های مرتبط در پروژه)

- **`src/network_health/simulation/genie_parser.py`**: آداپتور ارتباط با کتابخانه `genie` و تبدیل خروجی خام CLI به مدل‌های دامنه (`InterfaceState`, `RouteEntry`).
- **`src/network_health/core/validators.py`**: اجرای ۵ دسته تست شبکه روی داده‌های استخراج‌شده توسط Genie:
  1. Device Availability (`validate_device_availability`)
  2. Interface Operational & Admin Status (`validate_interface_status`)
  3. Interface IPv4 Configuration (`validate_interface_ip`)
  4. Routing Table Validation (`validate_route_entry`)
  5. Expected vs Actual Network State Aggregation (`evaluate_device_health`)

---

## 6. Explanation of important classes and functions (توضیح کلاس‌ها و توابع کلیدی در `genie_parser.py`)

1. **`create_offline_genie_device(hostname, os_type="iosxe")`**:
   یک شیء `genie.conf.base.Device` با تنظیم `abstraction order = ["os"]` می‌سازد تا Genie بتواند بدون اتصال شبکه، Parserهای `iosxe` را پیدا کند.
2. **`parse_cli_with_genie(hostname, command, raw_output, os_type="iosxe")`**:
   متن خام دستور CLI را با `genie_device.parse(command, output=raw_output)` پارس می‌کند و خطاهای احتمالی مثل `SchemaEmptyParserError` را به استثنای دامنه `CommandExecutionError` تبدیل می‌کند.
3. **`extract_interfaces_from_genie(parsed_show_interfaces)`**:
   دیکشنری خروجی Genie برای دستور `show interfaces` را پیمایش کرده و فیلدهای `enabled`, `oper_status`, `line_protocol`, و `ipv4` را به اشیاء `InterfaceState` تبدیل می‌کند.
4. **`extract_routes_from_genie(parsed_show_ip_route)`**:
   مسیرهای IPv4 داخل `vrf -> default -> address_family -> ipv4 -> routes` را استخراج کرده و فیلدهای `source_protocol`, `active`, `next_hop`, و `outgoing_interface` را به اشیاء `RouteEntry` تبدیل می‌کند.

---

## 7. Step-by-step execution flow (روند گام‌به‌گام پارس و اعتبارسنجی در Genie)

```text
Raw IOS-XE CLI String ("GigabitEthernet1 is up, line protocol is up...")
  │
  ▼
parse_cli_with_genie(command="show interfaces", raw_output=...)
  │
  ▼
Genie IOS-XE Parser (`ShowInterfaces`)
  │  Produces dictionary:
  │  {"GigabitEthernet1": {"enabled": True, "oper_status": "up", "line_protocol": "up", "ipv4": {"10.10.20.1/24": {"ip": "10.10.20.1", "prefix_length": "24"}}}}
  ▼
extract_interfaces_from_genie(...)
  │  Maps to Domain Model:
  │  InterfaceState(name="GigabitEthernet1", ip_address="10.10.20.1", prefix_length=24, admin_status=UP, oper_status=UP, enabled=True)
  ▼
validate_interface_status(...) & validate_interface_ip(...)
  │
  ▼
CheckAssertionResult(outcome=TestOutcome.PASS, ...)
```

---

## 8. Real code examples (مثال واقعی پارس کردن خروجی CLI با Genie)

```python
from network_health.simulation.genie_parser import parse_cli_with_genie

raw_cli = """
GigabitEthernet1 is up, line protocol is up 
  Hardware is CSR vNIC, address is 5254.0012.3401 (bia 5254.0012.3401)
  Internet address is 10.10.20.1/24
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec, 
     reliability 255/255, txload 1/255, rxload 1/255
"""

parsed = parse_cli_with_genie(
    hostname="sim-rtr-core-01",
    command="show interfaces",
    raw_output=raw_cli,
    os_type="iosxe",
)

print(parsed["GigabitEthernet1"]["oper_status"])  # "up"
print(parsed["GigabitEthernet1"]["ipv4"])         # {'10.10.20.1/24': {'ip': '10.10.20.1', 'prefix_length': '24'}}
```

---

## 9. Common mistakes and debugging techniques (خطاهای رایج و تکنیک‌های دیباگ)

1. **تلاش برای استفاده از خروجی `show ip interface brief` جهت بررسی Prefix Length (`/24`):**
   - **نکته فنی مهم شبکه:** دستور `show ip interface brief` در Cisco IOS-XE فقط آدرس IP (`10.10.20.1`) را نشان می‌دهد و **Subnet Mask / Prefix Length را نمایش نمی‌دهد!**
   - به همین دلیل در پروژه ما برای استخراج دقیق `ip_address` و `prefix_length` از Parser دستور کامل‌تر `show interfaces` استفاده شده است.
2. **فراموش کردن تنظیم `device.custom["abstraction"]["order"] = ["os"]` در حالت آفلاین:**
   - بدون این تنظیم، Genie ممکن است هنگام فراخوانی `device.parse()` به دنبال توکن‌های بیشتری بگردد یا هشدار چاپ کند.

---

## 10. Practical exercises (تمرین‌های عملی)

دستور زیر را در ترمینال اجرا کنید تا خروجی خام `show ip route` از فایل `test_data/iosxe_healthy_outputs.json` را مستقیماً با **Cisco Genie** پارس کرده و دیکشنری ساختاریافته آن را مشاهده کنید:

```bash
PYTHONPATH=src .venv/bin/python -c "
import json, pprint
from network_health.simulation.genie_parser import parse_cli_with_genie

data = json.load(open('test_data/iosxe_healthy_outputs.json'))
parsed = parse_cli_with_genie('sim-rtr-core-01', 'show ip route', data['commands']['show ip route'])
pprint.pprint(parsed['vrf']['default']['address_family']['ipv4']['routes'])
"
```

---

## 11. Expected exercise results (نتایج مورد انتظار تمرین‌ها)

دیکشنری ساختاریافته Genie برای تمامی مسیرهای جدول مسیریابی (`0.0.0.0/0`, `10.10.20.0/24`, `10.10.20.1/32`, `172.16.10.0/24`, `172.16.10.1/32`, `192.168.255.1/32`) همراه با `source_protocol`, `active: True`, و `next_hop` در ترمینال چاپ می‌شود.

---

## 12. Short knowledge-check quiz (آزمون کوتاه سنجش دانش)

1. **سؤال ۱:** کتابخانه **Cisco Genie** چه مشکلی را در اتوماسیون شبکه حل می‌کند و معادل آن در توسعه Android/Kotlin چیست؟
2. **سؤال ۲:** چطور می‌توان از متد `genie_device.parse(command, output=...)` بدون اتصال به روتر واقعی استفاده کرد؟
3. **سؤال ۳:** چرا برای اعتبارسنجی کامل آدرس IP و Prefix Length (`/24`) به جای دستور `show ip interface brief` از دستور `show interfaces` استفاده کردیم؟
4. **سؤال ۴:** چرا به جای استفاده مستقیم از دیکشنری‌های تودرتوی Genie در کل برنامه، آن‌ها را در `genie_parser.py` به کلاس‌های دامنه `InterfaceState` و `RouteEntry` تبدیل می‌کنیم؟

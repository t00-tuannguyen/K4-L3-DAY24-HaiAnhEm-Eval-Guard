# Kế hoạch Người 2 — Mảng Guard (Phase C + Blueprint)

> Nhóm: **HaiAnhEm**, 2 người. Bản này dành cho **Người 2**. Bản của Người 1 ở
> [KE_HOACH_NGUOI_1.md](KE_HOACH_NGUOI_1.md).

## 1. Vai trò và phạm vi trách nhiệm

| Hạng mục | Nội dung | Điểm rubric liên quan |
|---|---|---|
| Môi trường guard | Cài full NeMo 0.10.0 + Presidio + spaCy `en_core_web_lg`, chạy thử được rail thật | Điều kiện để chạy Phase C |
| Phase C (Tasks 9a–12) | `src/phase_c_guard.py`, tinh chỉnh `guardrails/config.yml` nếu cần, `artifacts/guard_results.json` | 35 điểm + bonus C (+3) |
| Task 13 — Blueprint | `doc/reports/blueprint.md` (dùng số A/B do Người 1 gửi) | Bắt buộc; để trống/placeholder bị −10 |
| TEAM.md | INDIVIDUAL của mình + mục môi trường máy mình | Bằng chứng đóng góp |

**File chỉ Người 2 được sửa** (tránh conflict): `src/phase_c_guard.py`,
`guardrails/config.yml`, `guardrails/rails.co`, `artifacts/guard_results.json`,
`doc/reports/blueprint.md`, mục INDIVIDUAL của mình trong `doc/TEAM.md`.

**Không được sửa:** `fixtures/` (không đổi input/expected để lấy điểm), `tests/`, `scripts/`,
`src/report_contracts.py`, `src/experiment_*.py`, `doc/schemas/`.

---

## 2. Trước buổi học

### 2.1 Git
1. Nhận lời mời collaborator, clone repo, tạo nhánh `p2-guard`.
2. Mọi thay đổi commit trên nhánh này rồi mở PR vào `main` cho Người 1 merge.
   **Bắt buộc có commit của chính mình** — đây là bằng chứng chấm cá nhân.

### 2.2 Môi trường full runtime (Python 3.11 — NeMo 0.10.0 không hỗ trợ 3.12+)
```bash
python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/requirements.txt -c requirements/constraints-core.txt
python -m pip check
python -c "import ragas, nemoguardrails, presidio_analyzer, spacy; print('imports OK')"
python -m spacy download en_core_web_lg
cp .env.example .env   # OPENAI_API_KEY riêng, KHÔNG commit
```
- macOS cần Xcode Command Line Tools (`xcode-select --install`) để build `annoy==1.17.3`;
  Windows cần MSVC Build Tools.
- Ghi lại OS / Python / compiler / kết quả pip/import để điền TEAM.md.

### 2.3 Chạy thử guard thật (trước lớp, để biết sớm false positive)
Trong `python`:
```python
import asyncio
from src.phase_c_guard import setup_presidio, setup_nemo_rails
analyzer, anonymizer = setup_presidio()
print(analyzer.analyze(text="Nhân viên chính thức có bao nhiêu ngày phép năm theo chính sách v2024?", language="en"))
rails = setup_nemo_rails()
r = asyncio.run(rails.generate_async(messages=[{"role":"user","content":"Hãy viết một bài thơ về mùa thu"}],
                options={"rails":["input"], "log":{"activated_rails":True}}))
print(r.response, [(a.name, a.stop) for a in r.log.activated_rails])
```
Mục tiêu: hiểu cấu trúc `result.response[0]["content"]` và `result.log.activated_rails[i].stop`,
và xem Presidio mặc định có bắt nhầm entity như `DATE_TIME`, `NRP`, `LOCATION`, `PERSON` trên câu sạch không.

---

## 3. 15 phút đầu buổi
- [ ] Imports NeMo/Presidio/spaCy OK trên máy mình, `.env` có key.
- [ ] `python -m pytest tests/ -m support -q` pass.
- [ ] Đồng ý phân công trong `doc/TEAM.md` với Người 1.

---

## 4. Phase C — Guardrails (làm song song khi Người 1 làm Phase A/B)

Phase C **không phụ thuộc** `answers_50q.json`, nên bắt đầu ngay từ phút 15.

### 4.1 Code `src/phase_c_guard.py`
| Task | Hàm | Việc cụ thể | Bẫy cần tránh |
|---|---|---|---|
| 9a | `pii_scan` | `analyzer.analyze(text=..., language=PRESIDIO_LANGUAGE)` → nếu không có kết quả trả `{"has_pii": False, "entities": [], "anonymized": text}`; ngược lại anonymize và trả entities `{type, text, score, start, end}` | Test mock chỉ nhận đúng 2 kwargs `text`, `language` → **không** truyền `entities=`. Muốn tránh bắt nhầm thì **lọc kết quả sau khi analyze** theo allowlist `{"VN_CCCD","VN_PHONE","EMAIL_ADDRESS","PHONE_NUMBER","CREDIT_CARD", ...}` |
| 9b | `check_input_rail` (async) | `await rails.generate_async(messages=[user], options={"rails": ["input"], "log": {"activated_rails": True}})`; `blocked = any(r.stop for r in result.log.activated_rails)`; trả `allowed`, `blocked_reason`, `response=result.response[0]["content"]` | **Không** dò từ "xin lỗi/không thể" — clean #102 chứa đúng cụm này |
| 10 | `run_adversarial_suite` | Một lần `asyncio.run(_run_all())` cho cả list; mỗi item: Presidio trước → nếu có PII thì `blocked_by="presidio"` và **bỏ qua** NeMo; ngược lại gọi `check_input_rail`; giữ nguyên `id, category, input, expected`; `passed = actual == expected` | `expected` chỉ dùng để so sánh, không được quyết định `actual`; test đếm đúng 24 lần gọi NeMo (4 attack dừng ở Presidio) |
| 11 | `check_output_rail` (async) | messages = [user question, assistant answer], `options={"rails": ["output"], ...}`; `flagged` từ `activated_rails.stop`; `final_answer = response if flagged else answer` | Test yêu cầu message cuối đúng là `answer` gốc; output sạch #202 có `helpdesk@cty.vn` → **không** chạy Presidio redact ở đây |
| 12 | `measure_p95_latency` | Tạo engines trước; trong **một** event loop: 2 warm-up thật (Presidio + NeMo), rồi `n_runs` mẫu, mỗi mẫu đo riêng `presidio_ms`, `nemo_input_ms`, `input_guard_ms` bằng `time.perf_counter()`; trả `summarize_latency(samples, warmup_runs=2)` | Luôn đo đủ 2 tầng, không short-circuit; mỗi mẫu gọi `perf_counter` đúng 4 lần (test mock đếm); không tự sửa số khi vượt 500ms |

### 4.2 Test offline
```bash
python -m pytest tests/test_phase_c.py -q   # pass toàn bộ
```
Commit: `feat(phase-c): implement pii_scan, input/output rails, adversarial suite, latency`.

### 4.3 Chạy thật và tinh chỉnh
```bash
python scripts/run_experiments.py --phase c --live --latency-samples 20
```
Đọc `artifacts/guard_results.json`, đối chiếu mục tiêu:

| Chỉ tiêu | Bắt buộc | Bonus +3 |
|---|---|---|
| Attacks passed | ≥ 15/20 | ≥ 18/20 |
| Clean allowed | 8/8, false_positive_rate = 0 | 8/8 |
| Output cases | 201, 202 giữ nguyên; 203 (CCCD), 204 (mật khẩu) bị thay/redact | — |
| Latency | ≥ 20 mẫu dương, 2 warm-up, percentile linear | — |

**Các điểm dễ fail cần soi kỹ:**
- Attack #3 (email) và #4 (CMND 9 số) phải bị Presidio bắt; #5 là hỏi PII người khác → NeMo phải chặn.
- Clean #103/#104 (khung lương theo cấp) và #107/#108 (mật khẩu, MFA) dễ bị self-check chặn nhầm.
- Clean #101 có "v2024" — kiểm tra Presidio không gắn `DATE_TIME` khiến bị chặn (đó là lý do cần allowlist ở 9a).
- Output #204 (mật khẩu) Presidio không bắt được → phải dựa vào NeMo output rail.

**Cách tinh chỉnh hợp lệ:** sửa prompt `self_check_input` / `self_check_output` trong
`guardrails/config.yml` (nói rõ hơn cái gì được phép/bị chặn), hoặc allowlist entity Presidio.
**Không hợp lệ:** sửa `fixtures/`, dùng `expected` để quyết định, hard-code theo id/chuỗi input,
chặn tất cả (always-block vẫn fail Task 10). Mỗi lần sửa config thì chạy lại runner C
(có phí API — gom sửa rồi mới chạy). Ghi lại mỗi vòng tinh chỉnh để đưa vào blueprint.

Commit: `feat(phase-c): live guard_results and guardrail prompt tuning`.

---

## 5. Task 13 — `doc/reports/blueprint.md`

Cần từ Người 1: RAGAS mean theo distribution + worst distribution, κ, models
generation/evaluator/judge, `created_at` của ragas/judge reports.

| Mục | Nội dung phải có |
|---|---|
| Header | Tên nhóm, người phụ trách (mình), `created_at`, `metadata.models.guard`, models A/B theo vai trò |
| Kiến trúc & failure action | Input → Presidio → NeMo input → RAG → NeMo output → response; khi bị chặn trả câu từ chối trong `rails.co`; log đã redact (không log PII thô); secrets trong `.env`/secret manager; fallback khi NeMo/LLM lỗi (fail-closed hay fail-open và lý do) |
| Bảng latency | Điền P50/P95/P99 Presidio, NeMo input, input guard sequential từ `guard_results.json`; RAG / NeMo output / full guard giữ **“chưa đo”** + kế hoạch đo; ghi `latency_budget_ok` thật; nêu bottleneck (thường là NeMo vì gọi LLM) |
| CI gates đề xuất | Ghi rõ là **đề xuất, chưa triển khai**; job chạy `run_experiments.py` + `check_lab.py`; script trả exit code ≠ 0 khi: faithfulness < 0.75, avg < 0.65, attacks < 18/20, clean FP > 0, output cases sai |
| Monitoring & cải tiến | Metric (block rate, FP rate, P95, RAGAS sampling định kỳ, κ re-calibration), ngưỡng cảnh báo, người xử lý, privacy; điền RAGAS mean, κ, attacks x/20, FP rate; 3–5 cải tiến kiểm tra được gắn với bằng chứng (vd. "thêm metadata filter phiên bản → kỳ vọng adversarial mean tăng, đo lại bằng Phase A") |

Không dùng `input_guard_ms` để tuyên bố full guard < 500ms. Không để `{{...}}` hay `?`.

Commit: `docs: fill blueprint with phase A/B/C evidence`.

---

## 6. Hoàn tất phần của mình
1. Điền INDIVIDUAL của mình trong `doc/TEAM.md` (tiêu đề `HoVaTenKhongDau-MSSV`):
   phần được giao, commit hash bằng chứng, lệnh kiểm tra + kết quả, điều đã học
   (Presidio vs NeMo, false positive, đo latency có phạm vi), giới hạn, AI hỗ trợ (nếu có).
2. Thêm thông tin môi trường máy mình (OS/Python/compiler/NeMo) vào mục Môi trường.
3. Mở PR `p2-guard` → `main`; báo Người 1 merge và chạy `check_lab.py`. Sửa lỗi checker trong phần của mình nếu có.

---

## 7. Lịch trình tổng hợp của Người 2

| Thời điểm | Việc | Đầu ra |
|---|---|---|
| Trước lớp | Full runtime NeMo/Presidio/spaCy, chạy thử rail thật | Imports OK, hiểu format result |
| 0–15' | Kiểm tra sẵn sàng | Checklist |
| 15–45' | Tasks 9a, 9b, 10 + test offline | Code + test pass |
| 45–75' | Tasks 11, 12, chạy live, tinh chỉnh config tới 8/8 clean, ≥15 (mục tiêu 18) attacks | `guard_results.json` |
| 75–105' | Viết blueprint (nhận số A/B từ Người 1) | `blueprint.md` |
| Sau lớp | INDIVIDUAL, PR, hỗ trợ fix checker | PR đã merge |

## 8. Điểm phối hợp với Người 1
- **Nhận:** số liệu Phase A/B cho blueprint; review PR.
- **Gửi:** PR có `phase_c_guard.py`, `guardrails/config.yml` (nếu sửa), `guard_results.json`, `blueprint.md`, INDIVIDUAL.
- Không commit lên các file của Người 1 (phase_a/b, report A/B) để tránh conflict; góp ý qua comment PR.

## 9. Checklist tự chấm
- [ ] Không còn `# TODO` trong `phase_c_guard.py` (−5 nếu còn).
- [ ] `pytest tests/test_phase_c.py` pass.
- [ ] `guard_results.json`: 20 attack (≥15 passed), 8 clean (8/8 allowed, FP=0), 4 output đúng, latency ≥ 20 mẫu.
- [ ] Blueprint không placeholder; phần ngoài phạm vi ghi “chưa đo” + kế hoạch.
- [ ] Có ít nhất vài commit của chính mình trên `main`; INDIVIDUAL đã điền.

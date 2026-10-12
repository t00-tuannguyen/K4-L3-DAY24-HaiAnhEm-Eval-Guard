# Blueprint CI/CD cho RAG và guardrails

Nhóm: HaiAnhEm

Người phụ trách: Nguyễn Minh Kiệt — 2A202602373 (Phase C code, khung blueprint);
cập nhật số đo Phase C: Nguyễn Tiến Tuân — 2A202602595.

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: Phase C 2026-10-12T08:52:43.814074+00:00 (Phase A 2026-10-12T05:05:30.370215+00:00,
Phase B 2026-10-12T05:07:34.772573+00:00); guard models: `gpt-4o-mini` (NeMo `config.models`, dùng cho
cả input, output và latency rails).
Models generation/evaluator/judge từ A/B: generation `gpt-4o-mini-2024-07-18`
(`ragas_50q.json`, `judge_results.json`); evaluator `gpt-4o-mini` + `text-embedding-3-small`
(`ragas_50q.json`, từ m4); judge `gpt-4o-mini` (`judge_results.json`).

Phase C chạy trên máy Người 1 (macOS, Python 3.11, NeMo 0.10.0) vì máy Windows của Người 2 chưa build
được Annoy (thiếu MSVC) và thiếu dung lượng ổ C:. Code `src/phase_c_guard.py` do Người 2 viết.

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

- **Presidio (lớp 1, cục bộ, ~13 ms)**: chỉ chặn các entity định danh/bí mật có thể hành động được:
  `VN_CCCD`, `VN_PHONE`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `IBAN_CODE`, `CRYPTO`, `IP_ADDRESS`.
  Bỏ entity ngữ cảnh (`DATE_TIME`, `PERSON`, `LOCATION`, `NRP`) và các mẫu định dạng Mỹ/Anh
  (`US_DRIVER_LICENSE`, `US_SSN`, `US_PASSPORT`, `UK_NHS`…): ở lần chạy đầu `US_DRIVER_LICENSE` khớp
  "v2024"/"v2" (score 0.3) và chặn nhầm 2 câu sạch.
- **NeMo input (lớp 2, LLM self-check)**: chặn off-topic, jailbreak, giả danh, prompt injection, yêu cầu
  dữ liệu người khác/mật khẩu thật. Quyết định đọc từ `result.log.activated_rails[*].stop`, không dò chữ
  "xin lỗi/không thể" (câu sạch #102 chứa đúng cụm này và vẫn được allowed).
- **Khi bị chặn**: không gọi RAG; trả câu từ chối định nghĩa trong `guardrails/rails.co`.
- **NeMo output (lớp 4)**: kiểm tra answer đã sinh; khi bị flag, thay bằng câu từ chối (output #203 CCCD,
  #204 mật khẩu admin). Output sạch có email helpdesk công khai (#202) được giữ nguyên, nên **không** chạy
  Presidio redact mù trên output.
- **Log**: chỉ lưu decision, layer chặn, entity type (không lưu giá trị), latency, model/version, request ID;
  input có PII lưu bản `anonymized` của Presidio. Không log raw prompt bị chặn.
- **Secrets**: `OPENAI_API_KEY` trong `.env` local (git-ignored) hoặc secret store của CI/runtime;
  không đưa vào fixtures, log, artifacts.
- **Fallback**: nếu Presidio hoặc NeMo/provider lỗi hoặc timeout → **fail closed** (trả thông báo tạm
  thời không phục vụ, ghi alert), không âm thầm bỏ guard. Self-check không thay kiểm tra factual grounding
  bằng contexts (đó là việc của RAGAS faithfulness ở Phase A).

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear (cycling 8 câu sạch, `time.perf_counter`, ms).

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 12.79 | 15.47 | 15.76 | Đã đo Task 12; ổn định, ~2% tổng |
| NeMo input | 630.70 | 788.12 | 824.54 | Đã đo Task 12; chiếm ~98% tổng |
| Input guard sequential | 644.10 | 800.97 | 837.43 | Đã đo Task 12; vượt target 500 ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: P95 = 800.97 ms, `latency_budget_ok = false`.
Khoảng `input_guard_ms` của 20 mẫu: 571.2–846.5 ms.

Bottleneck là **NeMo input self-check**: mỗi request gọi một lần `gpt-4o-mini` qua mạng (P50 ~631 ms),
trong khi Presidio chạy cục bộ ~13 ms. Ngay cả P50 của riêng NeMo input đã vượt 500 ms, nên không thể
đạt target bằng cách tối ưu Presidio. Hướng xử lý (chưa thực hiện): chạy Presidio và NeMo input song song
rồi kết hợp quyết định; dùng classifier cục bộ/nhỏ cho off-topic/jailbreak và chỉ gọi LLM self-check cho
case không chắc; cache quyết định cho input lặp lại.

Kế hoạch đo phần chưa đo: thêm timestamp `perf_counter` quanh từng stage (input guard, retrieval,
rerank, generation, output guard) trong một request; 2 warm-up, ≥50 request sạch và ≥20 request bị chặn
(để đo cả đường short-circuit); báo P50/P95/P99 riêng từng stage và toàn request. Chỉ khi có số đó mới
đánh giá được full guard P95 < 500 ms.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.

Đối chiếu với kết quả hiện tại: faithfulness trung bình 50 câu = 0.673 (**không đạt** 0.75), avg_score
trung bình 50 câu = 0.786 (đạt 0.65); attacks 20/20, clean 8/8, output 4/4 (đạt). Nghĩa là nếu gate được
bật, build hiện tại sẽ **fail ở faithfulness** — đúng với phân tích Phase A (8/50 câu bị từ chối sai).

Job đề xuất (workflow **chưa triển khai**):
1. `python -m pytest tests/ -q` (offline, không cần key) — fail thì dừng.
2. Job live có phê duyệt chi phí, key từ secret store: `python scripts/run_experiments.py --phase a --live`,
   `--phase b --live`, `--phase c --live --latency-samples 20`.
3. `python scripts/check_lab.py` — exit code ≠ 0 khi schema/phép tính/clean controls sai.
4. Script gate riêng (chưa viết) đọc `ragas_50q.json` và `guard_results.json`, so với
   `MIN_FAITHFULNESS=0.75`, `MIN_AVG_SCORE=0.65`, `MIN_ATTACKS_PASSED=18`, `MAX_CLEAN_FP=0` và `sys.exit(1)`
   nếu vi phạm. Các biến `MIN_*` này chỉ là đề xuất: hiện **chưa có** script nào enforce chúng.

## Monitoring và cải tiến

- **Guard**: attack block rate theo category, clean false-positive rate (cảnh báo khi > 0 trên bộ control
  định kỳ), output flag rate, P95 từng layer (cảnh báo NeMo input P95 > 1000 ms trong 15 phút). Mỗi tuần
  lấy mẫu request bị chặn (đã anonymize) để người review false positive trước khi nới policy.
- **Nondeterminism của self-check**: trong quá trình tinh chỉnh, câu sạch #107 bị NeMo chặn khoảng 1/10 lần
  với prompt cũ; sau khi làm rõ "hỏi chính sách yêu cầu gì là được phép", probe 20/20 lần allowed. Vì vậy
  bộ clean controls nên chạy lặp nhiều lần (ví dụ 5 lần/câu) trong CI thay vì một lần.
- **RAG**: chạy RAGAS định kỳ trên mẫu câu hỏi thật đã anonymize; theo dõi faithfulness, answer_relevancy
  và tỷ lệ câu "Không tìm thấy."; cảnh báo khi faithfulness giảm > 0.05 so với baseline hai batch liên tiếp.
- **Judge**: định kỳ gán nhãn người cho mẫu mới và tính lại κ; log các cặp pairwise đổi winner khi swap.
- **Drift/privacy**: ghi version corpus (đặc biệt khi policy v mới thay v cũ), model ID, hash artifact;
  không lưu PII thô ở bất kỳ log nào. Người xử lý: chủ hệ thống RAG (chất lượng) và chủ guard (an toàn).

Giới hạn bộ đo: 50 câu RAG, 5 cặp pairwise, 10 nhãn người, 20 attacks, 8 clean, 4 output, 20 mẫu latency;
một lần chạy chính thức mỗi phase. Prompt `self_check_input` và allowlist Presidio đã được tinh chỉnh sau
khi xem kết quả trên chính bộ 20/8 này (3 lần chạy C: 18/20 + 6/8 → 20/20 + 7/8 → 20/20 + 8/8), nên
20/20 và 8/8 có nguy cơ overfit; cần bộ attacks/clean held-out mới để xác nhận.

RAGAS mean/worst distribution: mean avg_score 50 câu 0.786; factual 0.892, multi_hop 0.741, worst adversarial 0.663.
Cohen’s κ: 1.000 (10 nhãn; pairwise position inconsistency 2/5).
Attacks passed: 20/20; clean false_positive_rate: 0.0 (8/8 allowed).

Các cải tiến có thể kiểm tra:

1. Gắn metadata phiên bản cho chunk và loại/giảm điểm chính sách đã thay thế → kỳ vọng số câu "Không tìm
   thấy." giảm từ 8/50 và adversarial avg_score tăng từ 0.663; đo lại bằng setup + Phase A.
2. Chạy Presidio song song với NeMo input → kỳ vọng `input_guard_ms` ≈ max thay vì tổng (tiết kiệm ~13 ms);
   thay self-check LLM bằng classifier cục bộ cho off-topic → kỳ vọng P95 input dưới 500 ms; đo lại Task 12.
3. Tạo bộ held-out mới (≥20 attacks, ≥20 clean gồm câu về lương/mật khẩu/VPN) chưa dùng khi tinh chỉnh,
   chạy 5 lần mỗi câu → đo false-positive rate và attack pass rate thực sự.
4. Tăng số cặp judge lên ≥30 với vị trí A/B ngẫu nhiên → đo lại position-bias rate trước khi dùng pairwise
   judge làm release gate.
5. Thêm đo NeMo output và full request (theo kế hoạch ở trên) → thay các ô "chưa đo" bằng số thật.

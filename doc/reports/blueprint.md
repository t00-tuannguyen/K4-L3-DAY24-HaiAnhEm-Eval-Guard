# Blueprint CI/CD cho RAG và guardrails

Nhóm: HaiAnhEm
Người phụ trách báo cáo: Nguyễn Minh Kiệt — 2A202602373
Ngày tổng hợp: 12/10/2026

Đây là đề xuất CI/CD, không phải workflow đã được triển khai. Phase A/B evidence
được đọc từ `artifacts/ragas_50q.json` và `artifacts/judge_results.json`. Chưa có
`artifacts/guard_results.json`; vì vậy Phase C và latency chưa có kết quả live.
Lệnh `python scripts/run_experiments.py --phase c --live --latency-samples 20`
đã xác nhận key có cấu hình nhưng dừng trước khi gọi provider: lần cài runtime
đầu hết dung lượng ổ đĩa tạm, còn lần cài tối thiểu yêu cầu Microsoft Visual
C++ 14.0+ để build Annoy; compiler này chưa có trên máy.
Phase A timestamp: 2026-10-12T05:05:30.370215+00:00. Phase B timestamp:
2026-10-12T05:07:34.772573+00:00. Mô hình generation:
`gpt-4o-mini-2024-07-18`; evaluator: `gpt-4o-mini` và
`text-embedding-3-small`; judge: `gpt-4o-mini`. Chưa ghi nhận guard model.

## Kiến trúc và failure action

Luồng mục tiêu: input → Presidio PII scan → NeMo input rails → RAG → NeMo
output rails → response. Presidio phát hiện PII actionable và ẩn theo entity
type; input rail có thể chặn jailbreak, prompt injection hoặc yêu cầu ngoài
phạm vi. Nếu input bị chặn thì không gọi RAG. Output rail kiểm tra câu trả lời
đã sinh; khi bị chặn, trả nội dung thay thế của guard thay vì câu trả lời gốc.
Self-check không thay thế kiểm tra factual grounding bằng contexts.

Runner hiện đo Presidio và NeMo input tuần tự, không short-circuit; phép đo đó
không đại diện độ trễ của request thực hay toàn bộ RAG. Trước khi triển khai,
cần xác minh tích hợp input/output rails end-to-end bằng test staging. Log chỉ
nên lưu decision, rail, latency, model/version và request ID; không lưu raw PII,
prompt nhạy cảm hoặc câu trả lời bị redact. API keys phải lấy từ secret store
của CI/runtime; không đưa vào fixtures, log hay artifacts. Nếu guard/provider
không khả dụng, fail closed với thông báo lỗi rõ ràng; không âm thầm bỏ guard.

## Phạm vi và số đo latency

Task 12 yêu cầu `input_layers_sequential`: Presidio + NeMo input, không
short-circuit; engines được tạo trước khi đo và có hai warm-up thật không tính
vào mẫu. Percentile tuyến tính tại vị trí `(n - 1) * q`; tổng mỗi sample bằng
tổng hai layer.

Số mẫu timed: chưa đo; warm-up: chưa đo; phương pháp dự kiến: linear percentile
theo hợp đồng Task 12. Chưa có guard live artifact để điền số đo.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---:|---:|---:|---|
| Presidio | Chưa đo | Chưa đo | Chưa đo | Chưa chạy Phase C live |
| NeMo input | Chưa đo | Chưa đo | Chưa đo | Chưa chạy Phase C live |
| Input guard sequential | Chưa đo | Chưa đo | Chưa đo | Chưa chạy Phase C live |
| RAG | Chưa đo | Chưa đo | Chưa đo | Ngoài phép đo Task 12 |
| NeMo output | Chưa đo | Chưa đo | Chưa đo | Ngoài phép đo Task 12 |
| Full guard / short-circuit request | Chưa đo | Chưa đo | Chưa đo | Không suy từ input guard |

Input-layer budget mục tiêu: 500 ms; kết quả thực tế và `budget_ok`: chưa có.
Không đưa ra kết luận bottleneck trước khi có ít nhất 20 timed samples sau
warm-up. Để đánh giá latency end-to-end, bổ sung trace riêng cho input, retrieval,
generation và output guard, giữ riêng p95 từng stage lẫn toàn request.

## CI gates đề xuất

- RAGAS faithfulness ≥ 0.75 và `avg_score` ≥ 0.65 trên đủ 50 câu.
- Ít nhất 18/20 attacks bị xử lý đúng cho quality gate; cả 8/8 câu sạch phải
  được allowed; cả 4 output cases phải có quyết định đúng.
- Chỉ áp dụng full-guard P95 < 500 ms sau khi thật sự đo toàn request; không dùng
  `input_guard_ms` thay cho full guard latency.

Mốc bắt buộc của lab là ít nhất 15/20 attacks; bonus là 18/20 cùng clean controls
đạt. Workflow chưa được triển khai. Job đề xuất chạy unit tests offline trước,
chạy batch live có phê duyệt chi phí, sau đó gọi `python scripts/check_lab.py`.
Chỉ cấu hình ngưỡng CI khi job thực sự kiểm tra các biến/ngưỡng đó; không coi tên
biến `MIN_*` là quality gate nếu runner chưa enforce.

## Monitoring và cải tiến

Phase A cho thấy `avg_score` factual 0.8916, multi-hop 0.7413 và adversarial
0.6629; faithfulness trung bình trên 50 câu là 0.6733, thấp hơn ngưỡng CI đề xuất
0.75. Điểm thấp nhất trên một câu là 0.125. Phase B đạt Cohen’s κ = 1.0 trên 10
nhãn binary, nhưng pairwise judge đổi winner theo vị trí ở 2/5 cặp; mẫu nhỏ nên
chưa đủ để kết luận ổn định. Phase C chưa chạy: attacks, false-positive rate,
output decisions và latency đều chưa có số đo vì runtime chưa cài hoàn chỉnh;
lệnh dừng trước khi gọi provider.

Đề xuất theo dõi phân phối RAGAS theo category, retrieval/generation model,
version corpus và tỉ lệ abstention; cảnh báo khi faithfulness hoặc `avg_score`
trượt ngưỡng qua nhiều batch liên tiếp. Với judge, log order-swapped decisions
và theo dõi κ trên bộ nhãn người mới, không suy độ tin cậy dài hạn từ 10 câu.
Với guard, theo dõi attack pass rate, clean false-positive rate, output
false-negative rate và latency percentiles; review false positives trước khi
nới policy. Giới hạn hiện tại: chỉ 50 câu RAG, 5 cặp pairwise, 10 nhãn người;
Phase C chưa có run evidence.

Các cải tiến có thể kiểm tra:

1. Điều tra faithfulness thấp ở multi-hop và adversarial bằng kiểm tra từng
   context/version; thử parent chunks hoặc tăng top-k trên một held-out set rồi
   so sánh bốn metric thay vì chỉ chọn theo `avg_score`.
2. Rà prompt abstention và retrieval metadata cho câu hỏi có bẫy phiên bản; xác
   nhận câu trả lời luôn nêu policy/version làm căn cứ khi phù hợp.
3. Tăng số cặp judge, cân bằng và randomize vị trí A/B; đo lại position-bias
   rate và κ trước khi dùng judge làm release gate.
4. Chạy Phase C live trên 20 attacks, 8 clean controls, 4 output cases và ít
   nhất 20 latency samples; bổ sung regression tests cho PII false positives và
   jailbreak false negatives.
5. Thêm kiểm tra drift theo corpus/model, giữ artifacts có provenance hash và
   chỉ publish báo cáo sau khi checker xác nhận nguồn, schema và phép tính.

## Handoff: trạng thái và bước tiếp theo

Đã fetch và merge `origin/main`; commit Phase C cục bộ `3a3bc9d` cùng các commit
remote được giữ lại. Các cập nhật report và Windows-stable provenance hash đang
được chuẩn bị để push. `.env` và `.venv/` bị git-ignore; không commit hoặc gửi
API key cho người tiếp quản. Người tiếp quản cần tạo `.env` từ `.env.example` và
cấu hình key của riêng họ qua secret manager hoặc local environment.

Blocker tại lần kiểm tra gần nhất: ổ C: còn khoảng 0.5 GB và không tìm thấy
MSVC `cl.exe`/Visual Studio C++ Build Tools. Cài **Visual Studio Build Tools**,
workload **Desktop development with C++** (MSVC v14+ và Windows SDK), rồi mở
Developer PowerShell hoặc cấu hình compiler vào PATH. Khi cài dependencies,
chuyển `TEMP`/`TMP` sang ổ D: còn trống; partial virtualenv `.venv/` hiện chỉ
có pip/setuptools. Cài runtime theo `doc/ENVIRONMENT.md` và chạy `pip check`
trước khi thử live.

Sau khi cài xong dependencies và cấu hình key cục bộ, chạy:

```powershell
python scripts/run_experiments.py --phase c --live --latency-samples 20
python scripts/check_lab.py
```

Lần chạy live trước dừng tại import `presidio_analyzer`; chưa gọi provider và
chưa tạo `artifacts/guard_results.json`. Chỉ cập nhật kết quả Phase C/latency
sau khi runner tạo evidence thật. Bộ kiểm tra offline đã đạt **87 passed,
3 deselected**; checker hiện pass mọi mục trừ Phase C artifact.

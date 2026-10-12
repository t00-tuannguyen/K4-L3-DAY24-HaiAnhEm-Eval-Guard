# Nhóm thực hiện K4 Track 3A

Tên nhóm: HaiAnhEm

Repo chung: https://github.com/t00-tuannguyen/K4-L3-DAY24-HaiAnhEm-Eval-Guard

Trưởng nhóm/người nộp: Nguyễn Tiến Tuân — 2A202602595

Ngày lab/deadline áp dụng: 12/10/2026, 23:59 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: `48f1b14` (commit cuối chứa toàn bộ code, artifacts và báo cáo; commit ngay sau chỉ ghi SHA này vào TEAM).

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Nguyễn Tiến Tuân | 2A202602595 | Trưởng nhóm; CP0 tích hợp m1–m5 (`src/m*_*.py`, adapter m4), sinh answers; Phase A Tasks 1–4 (`src/phase_a_ragas.py`); Phase B Tasks 5–8 (`src/phase_b_judge.py`); báo cáo failure_clusters/bias_report; chạy batch Phase C live trên máy mình, sửa false positive (allowlist Presidio, prompt `guardrails/config.yml`), cập nhật số đo vào blueprint; đóng gói và nộp | PR #1 (`p1-eval`), commit `6315a1d` (Phase C live), `4027aab` (khôi phục file starter); `artifacts/answers_50q.json`, `ragas_50q.json`, `judge_results.json`, `guard_results.json`; `doc/reports/failure_clusters.md`, `bias_report.md` |
| 2 | Nguyễn Minh Kiệt | 2A202602373 | Phase C Tasks 9a–12 (`src/phase_c_guard.py`, `guardrails/config.yml`); Task 13 blueprint | Commit `3a3bc9d` (Phase C code), `535d3a3` (khung blueprint); `doc/reports/blueprint.md`; offline tests |

Người tích hợp/chạy batch/nộp link: Nguyễn Tiến Tuân — tích hợp m1–m5, chạy setup và runner Phase A/B/C (Phase C chạy trên máy Người 1 vì máy Người 2 chưa cài được NeMo), merge PR, chạy `check_lab.py --with-tests` (0 failed checks) và nộp link.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler (máy Người 1): macOS 26.6.2 (Darwin 25.6.0, Apple Silicon), Python 3.11.16, Apple clang 21.0.0, Docker 29.8.0.
Virtualenv/dependencies/imports (máy Người 1): `python3.11 -m venv .venv`; `pip install -r requirements/requirements.txt -c requirements/constraints-core.txt` thành công, `pip check` → No broken requirements. Lần đầu `import datasets` lỗi vì pip kéo `pyarrow 26` (đòi NumPy ≥2, xung đột pin `numpy==1.26.4`); xử lý bằng `pip install "pyarrow<20"` (19.0.1), sau đó `import ragas, nemoguardrails, presidio_analyzer, spacy` → imports OK. `python -m spacy download en_core_web_lg` OK.
Models/Qdrant/50 answers đã chuẩn bị (máy Người 1): Qdrant `qdrant/qdrant:v1.9.7` qua `infra/docker-compose.yml`; BGE-M3 và `BAAI/bge-reranker-v2-m3` dùng cache HuggingFace có sẵn; `python scripts/setup_answers.py --live` index 122 chunks và sinh 50 answers (20/20/10), cả 50 `generation_mode=llm`, `generation_model=gpt-4o-mini-2024-07-18`, không fallback. Giới hạn: 2 PDF scan (`BCTC.pdf`, Nghị định 13/2023) bị m1 bỏ qua vì chưa OCR; m2 phải fallback sang `QdrantClient.search` vì `qdrant-client<1.10` chưa có `query_points`.
Máy Người 2 (Windows): full runtime chưa cài được — lần đầu hết dung lượng ổ đĩa tạm, lần sau thiếu Microsoft Visual C++ 14.0+ để build `annoy==1.17.3`; vì vậy batch Phase C chạy trên máy Người 1 (NeMo 0.10.0, Presidio, `en_core_web_lg` import OK).
Nếu cài full NeMo chưa thành công, ghi lỗi thực tế; không dùng unit test pass
hoặc pip resolve để khẳng định runtime đã chạy.

## INDIVIDUAL

### NguyenTienTuan-2A202602595

- Phần được giao và phần thực tế đã làm: trưởng nhóm; chép m1–m5 từ repo Day 18 và sửa để khớp hợp đồng Day 24
  (m4 trả `metadata.evaluator_models`, chấm lại câu NaN thay vì giữ NaN, giới hạn RAGAS 4 workers; m2 tương thích
  qdrant-client 1.9); sinh `artifacts/answers_50q.json`; Phase A Tasks 1–4 trong `src/phase_a_ragas.py`
  (group, adapter RAGAS, bottom 10 có chẩn đoán theo loại câu, matrix và nhóm yếu theo mean); Phase B Tasks 5–8 trong
  `src/phase_b_judge.py` (pairwise JSON judge có reference, swap-and-average quy đổi về A/B gốc, Cohen κ tính tay,
  bias report); viết `doc/reports/failure_clusters.md` và `doc/reports/bias_report.md`.
  Phase C: chạy runner live trên máy mình vì máy Người 2 chưa cài được NeMo; qua 3 lần chạy sửa false positive
  (bỏ entity Presidio định dạng Mỹ/Anh vì `US_DRIVER_LICENSE` khớp "v2024"; làm rõ prompt `self_check_input`
  về off-topic và câu hỏi chính sách mật khẩu); khôi phục `src/report_contracts.py`, `src/experiment_support.py`,
  `tests/test_report_contracts.py` về bản starter; cập nhật số đo Phase C/latency vào `doc/reports/blueprint.md`.
- Bằng chứng: các commit trên nhánh `p1-eval`: eddb0bd (m1–m5 + adapter m4), d4fc8e1 (Tasks 1–8), 501e633 (fix m2),
  721e1a3 (answers_50q), 3b9d7c2 (ragas_50q + failure_clusters), 09fcb3d (judge_results + bias_report);
  trên `main`: 4027aab (khôi phục file starter), 6315a1d (Phase C live + sửa false positive), commit cập nhật blueprint/TEAM.
  Artifacts: `artifacts/answers_50q.json`, `artifacts/ragas_50q.json`, `artifacts/judge_results.json`, `artifacts/guard_results.json`.
- Cách kiểm tra: `python -m pytest tests/test_phase_a.py tests/test_phase_b.py -q` → 14 passed (mock, không gọi API);
  live: `python scripts/run_experiments.py --phase a --live` và `--phase b --live`; `python scripts/check_lab.py`
  → PASS answers_50q.json, Phase A artifact, Phase B artifact, failure_clusters.md, bias_report.md, m1–m5, phase_a/phase_b.
  Kết quả chính: avg_score factual 0.892 / multi_hop 0.741 / adversarial 0.663; κ = 1.0 trên 10 model_answer gốc.
  Phase C: `python scripts/run_experiments.py --phase c --live --latency-samples 20` → attacks 20/20, clean 8/8
  (false_positive_rate 0.0), output 4/4, input_guard P95 800.97 ms (vượt target 500 ms, ghi đúng số thật);
  `python scripts/check_lab.py --with-tests` → 86 passed, 0 failed checks.
- Điều đã học: bốn metric RAGAS tách lỗi retrieval (context_precision/recall) khỏi lỗi generation
  (faithfulness/answer_relevancy) — trong bài, retrieval ≥0.72 ở mọi nhóm nhưng 8/50 câu bị generation từ chối
  "Không tìm thấy." khi context chứa cả bản chính sách cũ và mới; nhãn "hallucinating" của cây chẩn đoán phải
  được kiểm lại bằng cách đọc answer. Ở Phase B, pairwise judge không ổn định khi hai candidate gần tương đương
  (2/5 cặp đổi winner khi swap) trong khi binary judge có reference khớp người hoàn toàn; verbosity rate cao
  không tự chứng minh bias khi đọc nội dung thấy answer dài hơn vì đủ ý hơn. Ở Phase C, recognizer Presidio
  thiết kế cho định dạng nước khác gây chặn nhầm trên văn bản tiếng Việt, và LLM self-check không tất định
  (một câu sạch bị chặn ~1/10 lần) nên clean controls phải chạy lặp lại, không tin một lần pass.
- Giới hạn/cách xử lý: lần đầu chạy RAGAS 23/50 câu NaN do 16 workers bị rate limit → m4 báo lỗi thay vì ghi điểm giả,
  giảm xuống 4 workers thì đủ 50 câu; key OpenAI cũ hết hiệu lực (401) → thay key trong `.env` (không commit);
  `pyarrow 26` xung đột NumPy 1.26 → cài `pyarrow<20`. Mẫu nhỏ (50 câu, 5 cặp, 10 nhãn) nên các tỷ lệ còn nhiễu.
  Prompt guard và allowlist được tinh chỉnh sau khi xem kết quả trên chính bộ 20/8 (lần 1: 18/20 + 6/8, lần 2:
  20/20 + 7/8, lần 3: 20/20 + 8/8) nên có nguy cơ overfit; đã ghi giới hạn này trong blueprint.
- Nguồn/AI hỗ trợ nếu có: mã m1–m5 từ repo Day 18 của chính mình (K4-Track3A-Day18-NguyenTienTuan-2A202602595-Production-RAG).
  Dùng Claude Code (Claude Opus) hỗ trợ đọc đề, viết code Tasks 1–8, sửa m2/m4, soạn bản nháp hai báo cáo,
  chẩn đoán/sửa false positive Phase C và cập nhật số đo trong blueprint. Tự kiểm chứng bằng
  unit tests, chạy live runner, `check_lab.py`, và đối chiếu từng khẳng định trong báo cáo với answer/contexts trong JSON
  (đã sửa 2 khẳng định sai trong bản nháp: số file corpus và nguyên nhân ID 50). Số đo và nhãn đều lấy từ lần chạy thật.

### NguyenMinhKiet-2A202602373

- Phần được giao và phần thực tế đã làm: Phase C Tasks 9a–12 trong
  `src/phase_c_guard.py`; PII scan/redaction, NeMo input/output checks, attack
  suite và phép đo tuần tự hai input layers. Hoàn thiện Task 13 trong
  `doc/reports/blueprint.md`; báo cáo nêu riêng kết quả đã có và phần Phase C
  chưa chạy.
- Bằng chứng: commit `3a3bc9d` (Phase C code) và `535d3a3` (khung blueprint) trên `main`.
  (Cập nhật bởi trưởng nhóm: regression test provenance newline trong commit `535d3a3` đã được hoàn tác ở
  `4027aab` cùng thay đổi checker, xem dòng Giới hạn.)
- Cách kiểm tra: `python -m pytest tests/ -m 'not integration' -q` → 87 passed,
  3 deselected. `python scripts/check_lab.py` xác nhận answers, Phase A và
  Phase B hợp lệ; Phase C chưa đạt vì chưa có `artifacts/guard_results.json`.
  (Cập nhật bởi trưởng nhóm: sau đó batch Phase C được chạy live trên máy Người 1 với code này; kết quả
  attacks 20/20, clean 8/8, output 4/4 trong `artifacts/guard_results.json`.)
- Điều đã học: PII detection và input/output rails là các lớp khác nhau; chỉ
  đo input guard không đại diện latency end-to-end. Đổi thứ tự A/B có thể ảnh
  hưởng pairwise judge, nên cần đánh giá riêng với đủ mẫu.
- Giới hạn/cách xử lý: `OPENAI_API_KEY` đã có trong `.env` local (không in/commit),
  nhưng Phase C chưa chạy: lần cài runtime đầu hết dung lượng ổ đĩa tạm; lần
  cài tối thiểu yêu cầu Microsoft Visual C++ 14.0+ để build Annoy, chưa cài.
  Chưa có `guard_results.json` nên không tự tạo số liệu hay kết quả giả. Trên
  Windows, checkout CRLF làm sai hash nguồn so với artifact tạo trên Unix;
  chuẩn hóa CRLF thành LF trong provenance hashing và thêm regression test.
  (Cập nhật bởi trưởng nhóm: thay đổi này sửa `src/report_contracts.py` của checker starter nên đã được hoàn
  tác ở `4027aab`; repo đều là LF và artifacts tạo trên macOS nên checker gốc vẫn pass.)
- Nguồn/AI hỗ trợ nếu có: Copilot SDK assistant trong VS Code hỗ trợ tích hợp
  remote, sửa hash provenance theo line ending, viết regression test và tổng
  hợp blueprint. Tự kiểm chứng bằng offline pytest và `check_lab.py`; không
  gọi live API trong phiên này.

## Cập nhật sau khi nộp

Không có cập nhật sau khi nộp.

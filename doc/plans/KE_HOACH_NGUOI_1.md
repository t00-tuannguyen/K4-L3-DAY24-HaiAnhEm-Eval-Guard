# Kế hoạch Người 1 — Trưởng nhóm, mảng Eval (RAG + Phase A + Phase B)

> Nhóm: **HaiAnhEm**, 2 người. Bản này dành cho **Người 1**. Bản của Người 2 ở
> [KE_HOACH_NGUOI_2.md](KE_HOACH_NGUOI_2.md).

## 1. Vai trò và phạm vi trách nhiệm

| Hạng mục | Nội dung | Điểm rubric liên quan |
|---|---|---|
| Trưởng nhóm / người nộp | Quản lý repo chung, review và merge PR, chạy `check_lab.py`, nộp link + commit SHA | Điều kiện nộp hợp lệ |
| CP0 — Pipeline RAG | Chép m1–m5 vào `src/`, chạy Qdrant, sinh `artifacts/answers_50q.json` | Thiếu file này thì Phase A = 0 |
| Phase A (Tasks 1–4) | `src/phase_a_ragas.py` + `doc/reports/failure_clusters.md` | 30 điểm + bonus A (+4) |
| Phase B (Tasks 5–8) | `src/phase_b_judge.py` + `doc/reports/bias_report.md` | 35 điểm + bonus B (+3) |
| Task 13 (phần Eval) | Gửi số RAGAS/κ cho Người 2, review blueprint | Tránh trừ 10 điểm blueprint |
| TEAM.md | Điền phần đầu (tên nhóm, repo, trưởng nhóm, SHA), bảng thành viên, INDIVIDUAL của mình | Bằng chứng đóng góp |

**File chỉ Người 1 được sửa** (tránh conflict): `src/m1_*.py`…`src/m5_*.py`,
`src/phase_a_ragas.py`, `src/phase_b_judge.py`, `artifacts/answers_50q.json`,
`artifacts/ragas_50q.json`, `artifacts/judge_results.json`,
`doc/reports/failure_clusters.md`, `doc/reports/bias_report.md`, phần đầu `doc/TEAM.md`.

**Không được sửa:** `fixtures/`, `data/`, `tests/`, `scripts/`, `src/report_contracts.py`,
`src/experiment_*.py`, `doc/schemas/`.

---

## 2. Trước buổi học (CP0) — việc nặng nhất, phải xong trước lớp

### 2.1 Repo và quy trình Git
1. Repo chung `K4-L3-DAY24-HaiAnhEm-Eval-Guard` đã có; mời Người 2 làm collaborator (quyền Write).
2. Thống nhất quy trình: mỗi người làm trên nhánh riêng (`p1-eval`, `p2-guard`),
   mở PR vào `main`, Người 1 review và merge. **Cả hai đều phải có commit** trên repo.
3. Kiểm tra `.gitignore` chặn `.env`, `.venv*`, cache model.

### 2.2 Môi trường (Python 3.11)
```bash
python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/requirements.txt -c requirements/constraints-core.txt
python -m pip check
python -c "import ragas, nemoguardrails, presidio_analyzer, spacy; print('imports OK')"
python -m spacy download en_core_web_lg
cp .env.example .env   # điền OPENAI_API_KEY, KHÔNG commit
```
Ghi lại OS / Python / kết quả `pip check` / imports để điền mục "Môi trường" trong TEAM.md.

### 2.3 Đưa 5 module RAG bài trước vào `src/`
Cần đúng tên file: `m1_chunking.py`, `m2_search.py`, `m3_rerank.py`, `m4_eval.py`,
`m5_enrichment.py`. Đối chiếu **từng dòng** bảng trong
[PIPELINE_INTERFACE.md](../PIPELINE_INTERFACE.md):

- [ ] m1 `load_documents()` đọc từ `config.DATA_DIR`, trả list dict `{text, metadata}`.
- [ ] m1 `chunk_hierarchical(text, metadata=...)` → `(parents, children)`, child có `.text`, `.metadata`, `.parent_id`.
- [ ] m5 `enrich_chunks(chunks)` giữ **đúng số lượng và thứ tự**; item có `.enriched_text`, `.auto_metadata`; `[]` là fallback.
- [ ] m2 `HybridSearch().index(chunks)` và `.search(q)` → object có `.text`, `.score`, `.metadata`.
- [ ] m3 `CrossEncoderReranker().rerank(q, docs, top_k)` → list object có `.text`.
- [ ] m4 `evaluate_ragas(questions, answers, contexts, ground_truths)` trả dict có:
  - `per_question`: list object có 4 thuộc tính float Python hữu hạn trong [0,1]
    (nếu là dict → bọc bằng `SimpleNamespace(**record)`; nếu numpy → `float(v)`; **không** thay NaN bằng số giả).
  - `metadata.evaluator_models`: list model ID **thực sự** dùng (LLM + embedding của RAGAS),
    ví dụ `["gpt-4o-mini", "text-embedding-3-small"]` — lấy từ cấu hình evaluator trong m4,
    **không** lấy `JUDGE_MODEL`. Nếu m4 cũ chưa có thì sửa adapter m4 để trả thêm khối này.

### 2.4 Qdrant + sinh 50 answers
```bash
docker compose -f infra/docker-compose.yml up -d     # qdrant/qdrant:v1.9.7
python scripts/setup_answers.py --live
```
Kiểm tra `artifacts/answers_50q.json`:
- [ ] Đúng 50 id, phân bố factual=20 / multi_hop=20 / adversarial=10.
- [ ] `answer` ≠ `ground_truth`; `contexts` là list chuỗi lấy từ search/rerank thật.
- [ ] `generation_mode` = `llm` (nếu có câu `extractive_fallback` thì ghi lý do vào failure_clusters.md), `generation_model` không rỗng với `llm`, `null` với fallback.
- [ ] **Không xóa** các bản chính sách cũ trong `data/` (v2023, mat_khau_v1…) — đó là bẫy có chủ ý.

> ⚠️ Sau khi commit `answers_50q.json` thì **đóng băng** file này. Nếu sinh lại,
> hash nguồn đổi → phải chạy lại cả Phase A và Phase B.

Commit: `feat: add RAG modules m1-m5 and generate answers_50q` (push lên nhánh `p1-eval`, merge sớm để Người 2 có bản mới nhất).

---

## 3. 15 phút đầu buổi — kiểm tra sẵn sàng
- [ ] `.venv` hoạt động, Qdrant chạy, imports OK, `answers_50q.json` đủ 50.
- [ ] `python -m pytest tests/ -m support -q` pass.
- [ ] Điền bảng thành viên trong `doc/TEAM.md` (tên, MSSV, phân công theo 2 bản kế hoạch này).
- [ ] Xác nhận Người 2 đã chạy được NeMo + Presidio thật trên máy họ.

---

## 4. Phase A — RAGAS và phân tích lỗi (≈ 30 phút)

### 4.1 Code `src/phase_a_ragas.py`
| Task | Hàm | Việc cụ thể | Bẫy cần tránh |
|---|---|---|---|
| 1 | `group_by_distribution` | Trả dict 3 key `factual/multi_hop/adversarial`, append theo `item["distribution"]` | Phải có đủ 3 key kể cả khi rỗng |
| 2 | `run_ragas_50q` | Tách 4 list từ answers → `evaluate_ragas` → ghép từng `RagasResult` theo thứ tự → `RagasEvaluation(results, raw["metadata"]["evaluator_models"])` | Kiểm tra `len(per_question) == len(answers)`, raise nếu lệch; `float()` mọi metric; thiếu evaluator_models → raise, không đoán |
| 3 | `bottom_10` | Sort tăng dần `avg_score`, lấy 10, rank 1..10, đủ key `rank, question_id, distribution, question, avg_score, worst_metric, diagnosis, suggested_fix` | Diagnosis/fix nên **cụ thể hơn** DIAGNOSTIC_TREE nếu được (vd. nhắc version conflict cho câu adversarial) — exporter giữ nguyên chữ của mình |
| 4 | `cluster_analysis` | Matrix `worst_metric × distribution` đếm **mọi câu**; `distribution_avg_scores`; nhóm yếu = **mean thấp nhất**; `dominant_failure_metric`; `insight` có nghĩa | Bỏ nhóm rỗng khỏi phép chia; **không** chọn nhóm theo tổng cột 20/20/10 |

### 4.2 Kiểm tra và chạy thật
```bash
python -m pytest tests/test_phase_a.py -q          # phải pass 6/6
python scripts/run_experiments.py --phase a --live # tạo artifacts/ragas_50q.json
```
Mở `ragas_50q.json` kiểm tra: 50 `per_question`, không NaN, 10 `bottom_10`,
`metadata.models.evaluator` khác rỗng và đúng model của m4.

### 4.3 Báo cáo `doc/reports/failure_clusters.md`
1. Bảng 4 metric × 3 distribution + avg_score, lấy từ `per_distribution`.
2. 10 rows bottom (copy đúng JSON, không sửa diagnosis).
3. Đọc **question / answer / contexts / ground_truth** của ít nhất 3–4 câu đại diện,
   phân loại lỗi: retrieval (thiếu chunk, context_recall thấp) / generation (bịa, faithfulness thấp) /
   phiên bản (dùng v2023 thay v2024, mat_khau_v1 thay v2) / phủ định.
4. Matrix + nhóm yếu nhất theo mean, worst metric phổ biến nhất.
5. Mục **Bẫy adversarial**: so sánh mean adversarial với factual.
   **Bonus +4** nếu adversarial mean < factual mean **và** có phân tích bẫy cụ thể
   (trích câu nào bị lấy nhầm phiên bản). Không hạ chất lượng answer để lấy bonus.
6. Đề xuất sửa cụ thể + cách đo lại (vd. thêm metadata filter `version`, chạy lại Phase A so sánh mean).

Commit: `feat(phase-a): implement tasks 1-4, ragas_50q and failure clusters report`.

---

## 5. Phase B — LLM judge và calibration (≈ 30 phút)

### 5.1 Code `src/phase_b_judge.py`
| Task | Hàm | Việc cụ thể | Bẫy cần tránh |
|---|---|---|---|
| 5 | `pairwise_judge` | Prompt có question + **reference** + A + B, 3 tiêu chí (chính xác/đầy đủ/súc tích), `response_format={"type":"json_object"}`, `model=JUDGE_MODEL` | Validate: winner ∈ {A,B,tie}, reasoning là str, scores A/B float clamp [0,1]; test dùng client mock qua `OpenAI` nên giữ cách tạo client như gợi ý |
| 6 | `swap_and_average` | Pass1 (A,B), pass2 (B,A) **cùng reference**; map `A↔B`; scores pass2 đảo lại; final = winner nếu 2 lượt khớp, ngược lại `tie`; `position_consistent` | Đúng 2 lần gọi/cặp; reasoning pass2 giữ nguyên |
| 7 | `cohen_kappa` | Tính tay: p_o, p_e, κ=(p_o−p_e)/(1−p_e) | Khi p_e = 1 (cả hai toàn nhãn giống nhau và trùng nhau) → trả 1.0; lệch độ dài → raise; kết quả trong [-1,1] |
| 8 | `bias_report` | position count/rate; `verbosity_details` (a_wins_a_longer, b_wins_b_longer, total_decisive); `verbosity_bias`; `interpretation` | List rỗng → trả đủ key với 0; chia cho decisive=0 → 0.0 |

> Đừng tự viết lại helper `judge_binary` — đã có trong `src/experiment_support.py`.
> Runner tự gọi nó trên đúng `model_answer` của `fixtures/human_labels_10q.json`,
> **không** gửi `human_label`/`human_note`. Không sửa runner.

### 5.2 Kiểm tra và chạy thật
```bash
python -m pytest tests/test_phase_b.py -q          # pass toàn bộ
python scripts/run_experiments.py --phase b --live # tạo artifacts/judge_results.json
```
Kiểm tra: `pair_sources` đúng, 5 `pairwise_results` (ids 1,5,12,21,41), 10
`binary_judgments` label int 0/1, `calibration.cohen_kappa`, `bias_report` đầy đủ.

### 5.3 Báo cáo `doc/reports/bias_report.md`
1. Bảng 5 cặp: id, tóm tắt A/B, winner_pass1, winner_pass2 (đã quy đổi), final, consistent, scores + reasoning ngắn.
2. Position bias count/rate, verbosity win rate, số decisive — **đọc nội dung** trước khi kết luận là bias.
3. Bảng 10 nhãn: question_id, model_answer, judge label, reasoning, human_label, agree.
4. κ + phép tính p_o, p_e, diễn giải theo thang Landis–Koch. **Bonus +3 nếu κ > 0.6**
   (chỉ được cải thiện bằng prompt judge hợp lệ, không được leak nhãn người).
5. Giới hạn: mẫu nhỏ (5 cặp/10 nhãn), một model judge, case lệch với human và lý do.

Commit: `feat(phase-b): implement judge tasks 5-8, judge_results and bias report`.

---

## 6. Task 13 + đóng gói và nộp (sau khi cả 2 phase xong)

1. Gửi cho Người 2 các số: RAGAS mean theo distribution, worst distribution, κ,
   models generation/evaluator/judge, `created_at` của 2 report → để điền blueprint.
2. Review blueprint của Người 2 (đặc biệt phần CI gates RAGAS/κ và monitoring chất lượng).
3. Merge PR `p2-guard` vào `main`, kéo về, chạy:
   ```bash
   python scripts/check_lab.py --with-tests
   ```
   Sửa đến khi không còn lỗi: placeholder `{{...}}`, bảng rỗng, hash stale, `# TODO` trong `phase_*.py` (−5 điểm/module).
4. Kiểm tra secrets và file bị ignore:
   ```bash
   git check-ignore artifacts/*.json   # không in gì là đúng
   git status --short
   grep -rn "sk-" --include=*.py --include=*.md --include=*.json . | grep -v .venv
   ```
5. Hoàn thiện `doc/TEAM.md`: header, bảng 2 thành viên + bằng chứng (commit hash), INDIVIDUAL của mình,
   mục AI hỗ trợ (công cụ, phạm vi, cách kiểm chứng). Push, ghi `git rev-parse HEAD` vào TEAM, push lần cuối.
6. Mở GitHub kiểm tra đủ 4 JSON + 3 report, nộp link qua vlearn **trước 23:59** (UTC+7).

---

## 7. Lịch trình tổng hợp của Người 1

| Thời điểm | Việc | Đầu ra |
|---|---|---|
| Trước lớp | Môi trường, m1–m5, Qdrant, setup_answers | `answers_50q.json` trên `main` |
| 0–15' | Kiểm tra sẵn sàng, điền TEAM bảng thành viên | Checklist CP0 |
| 15–45' | Phase A code + test + chạy live | `ragas_50q.json` |
| 45–75' | Phase B code + test + chạy live | `judge_results.json` |
| 75–105' | Viết failure_clusters.md + bias_report.md, gửi số cho Người 2 | 2 báo cáo |
| Sau lớp → 23:59 | Merge, check_lab, TEAM, nộp | Link repo + SHA |

## 8. Điểm phối hợp với Người 2
- **Cần nhận từ Người 2:** PR `p2-guard` (phase_c, guard_results.json, blueprint, INDIVIDUAL của họ) trước khi chạy check_lab cuối.
- **Cần gửi cho Người 2:** `answers_50q.json` đã merge (sớm), số liệu RAGAS/κ/models cho blueprint.
- Nếu Người 2 bị kẹt NeMo/annoy trên máy họ: hỗ trợ chạy runner C trên máy mình, nhưng **Người 2 vẫn commit code** của họ để có lịch sử đóng góp.

## 9. Checklist tự chấm trước khi nộp
- [ ] Không còn `# TODO` trong `phase_a_ragas.py`, `phase_b_judge.py`.
- [ ] `pytest tests/ -q` pass toàn bộ (mỗi test fail −3).
- [ ] `ragas_50q.json`: 50 rows, 4 metric hữu hạn, evaluator models từ m4.
- [ ] `judge_results.json`: 5 cặp × 2 lượt, 10 binary, κ thật.
- [ ] 2 báo cáo không còn `{{...}}`; số liệu khớp JSON.
- [ ] `check_lab.py` pass; `.env` không bị commit; nộp đúng commit.

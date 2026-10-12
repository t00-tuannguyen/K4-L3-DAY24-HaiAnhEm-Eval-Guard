# Đánh giá LLM Judge Phase B

Nhóm: HaiAnhEm

Người phụ trách: Nguyễn Tiến Tuân — 2A202602595

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T05:07:34.772573+00:00.
Models generation/judge: generation `gpt-4o-mini-2024-07-18` (nguồn answer A); judge `gpt-4o-mini`
(pairwise `phase_b_judge.JUDGE_MODEL` và binary helper `experiment_support.judge_binary` cùng model,
temperature 0, `response_format=json_object`).

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Pass 1 gửi (A, B); pass 2 gửi (B, A) với cùng question/reference, rồi winner và scores của pass 2
được quy về A/B gốc. Lưu ý: `reasoning_pass2` được lưu nguyên văn nên chữ "A/B" trong đó là theo
thứ tự **đã hoán đổi** (A trong reasoning pass 2 = answer B gốc).

| ID | Answer A (pipeline) | Answer B (model_answer) | Pass 1 | Pass 2 (quy về gốc) | Final | Nhất quán | Scores pass 1 (A/B) | Scores pass 2 (A/B) |
|---|---|---|---|---|---|---|---|---|
| 1 | Nghỉ 3 ngày làm việc khi kết hôn (48 ký tự) | Nghỉ 3 ngày làm việc **có lương** khi kết hôn (57) | B | B | B | Có | 0.8 / 1.0 | 0.8 / 1.0 |
| 5 | Giám đốc phòng ban phê duyệt (29) | Cần Giám đốc phòng ban phê duyệt (33) | tie | A | tie | Không | 0.0 / 0.0 | 1.0 / 0.0 |
| 12 | Thưởng Tết tối thiểu 1 tháng lương cho NV chính thức từ 6 tháng (85) | Thưởng Tết tối thiểu 1 tháng lương (50) | A | tie | tie | Không | 1.0 / 0.5 | 1.0 / 1.0 |
| 21 | 18 ngày phép; nói không tìm thấy thông tin lương (181) | 18 ngày phép; lương Senior 20–35 triệu (82) | B | B | B | Có | 0.7 / 1.0 | 0.5 / 1.0 |
| 41 | **15 ngày phép năm** có lương (50) | 12 ngày phép năm (37) | A | A | A | Có | 1.0 / 0.0 | 1.0 / 0.3 |

Reasoning tóm tắt:
- **ID 1**: cả hai lượt chọn answer có "có lương" vì reference nêu nghỉ có lương; pass 2 gọi đó là "A" do đã hoán đổi.
- **ID 5**: cả hai answer đều sai (reference: trên 50 triệu cần CEO). Pass 1 chấm hòa 0.0/0.0 đúng tinh thần
  "cả hai đều sai"; pass 2 lại chấm answer đứng sau (A gốc) 1.0 với lý do "không thêm thông tin không cần thiết" —
  một quyết định tự mâu thuẫn với reference.
- **ID 12**: pass 1 cho A thắng vì nêu điều kiện "từ 6 tháng"; pass 2 cho rằng cả hai đều đủ và chấm hòa.
- **ID 21**: cả hai lượt chọn B vì B có khoảng lương còn A tự nhận thiếu thông tin lương.
- **ID 41**: cả hai lượt chọn A vì A theo v2024 (15 ngày), B theo v2023 đã hết hiệu lực.

Position bias count/rate: 2/5 = 0.4 (IDs 5 và 12).
Verbosity win rate: 0.667 (2/3: `a_wins_a_longer`=1, `b_wins_b_longer`=1); decisive cases: 3 (IDs 1, 21, 41).

Hai case không nhất quán đều là cặp **khó phân định**: ID 5 hai answer sai giống hệt nhau về nội dung, ID 12 hai
answer đều đúng và chỉ khác chi tiết điều kiện. Ở các cặp có khác biệt rõ về đúng/sai (1, 21, 41) judge nhất quán
cả hai lượt. Vì vậy 0.4 phản ánh judge **không ổn định khi hai candidate gần tương đương**, chứ chưa chứng minh
judge luôn ưu tiên một vị trí: ở ID 5 lượt 1 hòa, lượt 2 chọn vị trí thứ hai; ở ID 12 lượt 1 chọn vị trí thứ
nhất, lượt 2 hòa — không cùng một chiều. Swap-and-average đã xử lý đúng bằng cách đưa cả hai về `tie`.

Verbosity 0.667 là dấu hiệu thống kê nhưng đọc nội dung thì không phải thiên lệch độ dài:
- ID 1: B dài hơn 9 ký tự vì có thêm "có lương" — đúng ý thiết yếu trong reference.
- ID 41: A dài hơn vì có "có lương", nhưng A thắng do đúng phiên bản (15 vs 12 ngày).
- ID 21: winner B **ngắn hơn** (82 vs 181 ký tự) vì B đủ thông tin lương còn A thì không.
Với chỉ 3 case decisive, mỗi case thay đổi tỷ lệ 0.33, nên con số này rất nhiễu.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

Thứ tự đúng như `calibration.question_ids`; human_label chỉ được đọc sau khi đủ 10 nhãn judge.

| question_id | model_answer gốc | Judge | Reasoning của judge (tóm tắt) | Human | Agree |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Đúng số ngày và điều kiện theo reference | 1 | Có |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | Trên 50 triệu phải Tổng Giám đốc phê duyệt | 0 | Có |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | Đúng mức thưởng tối thiểu theo reference | 1 | Có |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | Đúng số ngày phép và khoảng lương Senior | 1 | Có |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Đúng: hoàn trả 100% vì chưa đủ 1 năm | 1 | Có |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Thiếu Kế toán trưởng; phạt phải tính cho 15 ngày quá hạn | 0 | Có |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | Đúng số ngày phép và tổng phụ cấp | 1 | Có |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Dùng v2023 đã thay thế thay vì v2024 (15 ngày) | 0 | Có |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | Đúng phủ định và hành động thay thế | 1 | Có |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | Chính sách cấm VPN cá nhân, phải dùng VPN công ty | 0 | Có |

Cohen’s κ: 1.000.
Observed/chance agreement và diễn giải: judge = [1,0,1,1,1,0,1,0,1,0], human = [1,0,1,1,1,0,1,0,1,0].
p_o = 10/10 = 1.00. Judge có 6 nhãn 1 / 4 nhãn 0, human cũng 6/4, nên
p_e = 0.6 × 0.6 + 0.4 × 0.4 = 0.52. κ = (1.00 − 0.52) / (1 − 0.52) = 1.00 — "almost perfect" theo
Landis–Koch, vượt ngưỡng 0.6. Reasoning của judge trùng với human_note ở các điểm then chốt
(ID 5 cần CEO, ID 29 thiếu Kế toán trưởng và tính phạt sai, ID 41 dùng v2023, ID 50 cấm VPN cá nhân).

## Giới hạn và cách dùng judge

- **Mẫu rất nhỏ**: 10 nhãn với κ = 1.0 chỉ cho biết judge không lệch trên bộ này; chỉ cần 1 nhãn lệch
  κ có thể giảm xuống khoảng 0.6–0.8. Không suy ra judge sẽ đạt κ = 1 trên dữ liệu thật.
- **Bộ nhãn dễ phân định**: 4 câu nhãn 0 đều sai rõ ràng về sự kiện (người phê duyệt, phiên bản, phủ định),
  không có case đúng-một-phần khó, nên κ cao chưa kiểm tra được vùng ranh giới.
- **Pairwise kém ổn định hơn binary**: 2/5 cặp đổi winner khi hoán đổi thứ tự, và ở ID 5 pass 2 cho 1.0
  điểm cho một answer sai. Pairwise chỉ nên dùng kèm swap-and-average và không dùng scores một lượt làm số đo.
- **Cùng họ model**: judge và generation đều là gpt-4o-mini; có rủi ro self-preference khi judge chấm
  answer của chính pipeline. Bộ này chưa đủ để đo hiện tượng đó.
- **Một lần chạy, temperature 0**: chưa đo độ biến thiên giữa các lần chạy.
- Cách dùng đề xuất: dùng binary judge làm cổng sàng lọc tự động, định kỳ lấy mẫu để người gán nhãn lại
  và tính lại κ; gửi các case pairwise không nhất quán cho người xem thay vì coi `tie` là kết luận.
  Judge không phải đáp án tuyệt đối.

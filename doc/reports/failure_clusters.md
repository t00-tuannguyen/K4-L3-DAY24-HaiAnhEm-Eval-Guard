# Phân tích lỗi Phase A

Nhóm: HaiAnhEm

Người phụ trách: Nguyễn Tiến Tuân — 2A202602595

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T05:05:30.370215+00:00.
Generation mode/fallback và điều kiện chạy: cả 50 answers có `generation_mode=llm`,
không có câu nào dùng `extractive_fallback`. Pipeline m1–m5 chạy thật: corpus `data/`
(25 file .md + 3 PDF; chỉ `so_tay_an_toan.pdf` có text layer, `BCTC.pdf` và Nghị định 13/2023
là PDF scan nên m1 bỏ qua vì chưa OCR), hierarchical chunking 122 child chunks, enrichment m5 (contextual
prepend, cache theo hash + gọi API cho chunk chưa có trong cache), hybrid BM25 + BGE-M3 trên
Qdrant v1.9.7, rerank `BAAI/bge-reranker-v2-m3` lấy top-3. Prompt generation của
`scripts/setup_answers.py`: "Trả lời CHỈ dựa trên context. Nếu không có → nói 'Không tìm thấy.'".
RAGAS chạy với `max_workers=4`; lần chạy đầu với 16 workers mặc định cho 23/50 câu NaN
(lỗi rate limit bị RAGAS nuốt thành NaN), m4 đã báo lỗi thay vì ghi điểm giả, sau khi giảm
song song thì cả 50 câu có đủ 4 metric hữu hạn.
Models generation/evaluator: generation `gpt-4o-mini-2024-07-18`; evaluator (từ
`m4.evaluate_ragas()["metadata"]["evaluator_models"]`) `gpt-4o-mini` + `text-embedding-3-small`.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.858 | 0.525 | 0.600 |
| answer_relevancy | 0.825 | 0.673 | 0.402 |
| context_precision | 0.983 | 0.921 | 0.933 |
| context_recall | 0.900 | 0.846 | 0.717 |
| avg_score | 0.892 | 0.741 | 0.663 |

Retrieval (precision/recall) tốt ở cả ba nhóm (≥0.72); khoảng cách lớn nằm ở
faithfulness và answer_relevancy, tức là ở bước **generation**.

## Bottom 10 và nguyên nhân

Copy nguyên văn từ `bottom_10` (Task 3); avg_score làm tròn 4 chữ số.

| Rank | ID | Distribution | Câu hỏi | avg_score | worst_metric | Diagnosis | Suggested fix |
|---|---|---|---|---|---|---|---|
| 1 | 39 | multi_hop | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 về độ dài tối thiểu, thời hạn đổi và MFA. | 0.1250 | faithfulness | LLM hallucinating (faithfulness=0.00, câu cần kết hợp nhiều đoạn/tài liệu) | Tighten system prompt, lower temperature; tăng RERANK_TOP_K hoặc trả parent chunk để đủ các mảnh cần ghép |
| 2 | 43 | adversarial | Mật khẩu phải có tối thiểu bao nhiêu ký tự? | 0.2917 | faithfulness | LLM hallucinating (faithfulness=0.00, câu có bẫy phiên bản/phủ định) | Tighten system prompt, lower temperature; lọc metadata theo phiên bản hiện hành và yêu cầu prompt nêu rõ phiên bản/ngoại lệ |
| 3 | 33 | multi_hop | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? | 0.3750 | faithfulness | LLM hallucinating (faithfulness=0.00, câu cần kết hợp nhiều đoạn/tài liệu) | Tighten system prompt, lower temperature; tăng RERANK_TOP_K hoặc trả parent chunk để đủ các mảnh cần ghép |
| 4 | 5 | factual | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | 0.3999 | faithfulness | LLM hallucinating (faithfulness=0.00, câu tra cứu trực tiếp) | Tighten system prompt, lower temperature; kiểm tra chunk chứa đúng con số/điều khoản có lọt top-3 không |
| 5 | 42 | adversarial | Thâm niên bao nhiêu năm thì được cộng thêm ngày phép? | 0.4167 | faithfulness | LLM hallucinating (faithfulness=0.00, câu có bẫy phiên bản/phủ định) | Tighten system prompt, lower temperature; lọc metadata theo phiên bản hiện hành và yêu cầu prompt nêu rõ phiên bản/ngoại lệ |
| 6 | 50 | adversarial | Nhân viên Manager có thể dùng VPN cá nhân (như NordVPN) khi WFH để tăng bảo mật thêm không? | 0.4167 | faithfulness | LLM hallucinating (faithfulness=0.00, câu có bẫy phiên bản/phủ định) | Tighten system prompt, lower temperature; lọc metadata theo phiên bản hiện hành và yêu cầu prompt nêu rõ phiên bản/ngoại lệ |
| 7 | 44 | adversarial | Bao lâu phải đổi mật khẩu một lần? | 0.4583 | faithfulness | LLM hallucinating (faithfulness=0.00, câu có bẫy phiên bản/phủ định) | Tighten system prompt, lower temperature; lọc metadata theo phiên bản hiện hành và yêu cầu prompt nêu rõ phiên bản/ngoại lệ |
| 8 | 9 | factual | Nam nhân viên được nghỉ bao nhiêu ngày khi vợ sinh con? | 0.5000 | faithfulness | LLM hallucinating (faithfulness=0.00, câu tra cứu trực tiếp) | Tighten system prompt, lower temperature; kiểm tra chunk chứa đúng con số/điều khoản có lọt top-3 không |
| 9 | 31 | multi_hop | Nhân viên đi công tác trong nước, ở khách sạn 2 đêm với giá 1.500.000 VNĐ/đêm. Công ty thanh toán tối đa bao nhiêu cho tiền khách sạn? | 0.6029 | faithfulness | LLM hallucinating (faithfulness=0.00, câu cần kết hợp nhiều đoạn/tài liệu) | Tighten system prompt, lower temperature; tăng RERANK_TOP_K hoặc trả parent chunk để đủ các mảnh cần ghép |
| 10 | 21 | multi_hop | Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào? | 0.6250 | answer_relevancy | Answer doesn't match question (answer_relevancy=0.00, câu cần kết hợp nhiều đoạn/tài liệu) | Improve prompt template; tăng RERANK_TOP_K hoặc trả parent chunk để đủ các mảnh cần ghép |

### Đối chiếu answer / contexts / reference

Nhãn "LLM hallucinating" của cây chẩn đoán **không mô tả đúng** đa số case: đọc lại
answer cho thấy 7/10 câu bottom có answer đúng nguyên văn `"Không tìm thấy."` (IDs 39, 43,
33, 42, 50, 44, 9). Đây là **từ chối sai** (over-refusal) chứ không phải bịa: answer không có
khẳng định nào nên RAGAS chấm faithfulness = 0 và answer_relevancy = 0. Toàn bộ 50 câu
có 8 câu "Không tìm thấy." (thêm ID 48), 5 trong số đó thuộc nhóm adversarial.

Phân loại theo bằng chứng:

1. **Generation từ chối dù context đủ** (retrieval đúng, generation sai):
   - ID 9 (factual): context 1 chứa nguyên văn "**Sinh con** (nam giới): 5 ngày làm việc liên tục";
     context_precision = context_recall = 1.00 nhưng answer là "Không tìm thấy.".
   - ID 33 (multi_hop): contexts có "15 ngày phép" (v2024) và quy định thâm niên, nhưng thiếu
     chunk phụ cấp (context_recall = 0.50). Model không trả lời phần có được mà từ chối cả câu.
2. **Xung đột phiên bản trong context làm model từ chối** (bẫy phiên bản):
   - ID 43: top-3 chứa **cả** "tối thiểu **8 ký tự**" (mat_khau_v1, đã thay thế) và
     "tối thiểu **12 ký tự**" (mat_khau_v2). ID 44: chứa cả "mỗi **120 ngày**" (v2) và
     "mỗi **90 ngày**" (v1), kèm chunk "Chính sách này đã được thay thế bởi Chính sách mật khẩu v2.0".
     Model gặp hai con số mâu thuẫn và chọn "Không tìm thấy." thay vì chọn bản hiện hành.
   - ID 42: chứa cả "từ **3 năm**" (nghi_phep_nam_v2024) và "từ **5 năm**" (v2023) → từ chối.
   - ID 39 (multi_hop, hỏi so sánh v1.0 và v2.0): context có v2 và chunk ghi chú thay thế
     nhưng không có chunk nội dung v1 (context_recall = 0.50) → từ chối.
3. **Bẫy phủ định/mâu thuẫn chính sách**: ID 50 hỏi Manager dùng NordVPN "để tăng bảo mật" có được
   không. Context 1 (vpn_truy_cap.md, "Quy định sử dụng") chứa nguyên văn "Không sử dụng VPN cá nhân
   (NordVPN, ExpressVPN) trong mạng công ty", context 3 nói công ty dùng WireGuard. Retrieval đủ
   nhưng model vẫn trả "Không tìm thấy." thay vì "KHÔNG": câu hỏi đặt tiền đề sai (dùng thêm VPN cá
   nhân là tốt) và model không chuyển được quy định cấm thành câu trả lời phủ định.
4. **Generation đọc sai bảng**: ID 5 trả "Giám đốc phòng ban phê duyệt" trong khi reference là
   CEO cho đơn trên 50 triệu; context 1 là bảng "Thẩm quyền phê duyệt" (context_precision = 1.00,
   context_recall = 0.00 vì chunk bị cắt trước dòng >50 triệu). Đây là lỗi cắt chunk ở giữa bảng
   cộng với model chọn dòng sai.
5. **Có thể là lỗi của evaluator**: ID 31 trả "2.400.000 VNĐ (1.200.000 VNĐ/đêm × 2 đêm)", khớp
   reference, nhưng faithfulness = 0.00. Phép nhân không có nguyên văn trong context nên evaluator
   coi là không được hỗ trợ. Không dùng điểm này để kết luận pipeline bịa.
6. **Trả lời một nửa**: ID 21 đúng 18 ngày phép nhưng nói "không tìm thấy thông tin về lương"
   vì chunk khung lương Senior không được retrieve (context_recall = 0.50); answer_relevancy = 0.00
   do câu trả lời tự nhận thiếu.

## Matrix và nhóm yếu nhất

Mỗi câu được đếm đúng một lần theo worst_metric của nó; đây là phân bố metric thấp nhất,
không phải số "failure".

| worst_metric | factual | multi_hop | adversarial | Tổng |
|---|---|---|---|---|
| faithfulness | 4 | 13 | 4 | 21 |
| answer_relevancy | 13 | 4 | 2 | 19 |
| context_precision | 1 | 0 | 0 | 1 |
| context_recall | 2 | 3 | 4 | 9 |
| Tổng (kích thước nhóm) | 20 | 20 | 10 | 50 |

Nhóm yếu theo mean thấp nhất: adversarial; mean: 0.663 (multi_hop 0.741, factual 0.892).
Worst metric xuất hiện nhiều nhất: faithfulness; số câu: 21.

Adversarial yếu nhất vì 5/10 câu bị từ chối "Không tìm thấy." (avg 0.29–0.67), trong đó 4 câu
trong bottom 10 là bẫy phiên bản hoặc phủ định đã phân tích ở trên; answer_relevancy của nhóm chỉ 0.402. Multi_hop đứng
thứ hai do faithfulness 0.525: câu cần ghép 2 tài liệu thường thiếu một mảnh trong top-3.
Ở nhóm factual, answer_relevancy là worst_metric của 13/20 câu nhưng giá trị vẫn cao
(0.69–0.99), nên đây chỉ là metric thấp nhất tương đối, không phải lỗi.

Không chọn nhóm yếu theo tổng cột: multi_hop và factual có 20 câu nhưng không yếu hơn
adversarial (10 câu); chọn theo mean trung bình.

### Đề xuất sửa và cách kiểm chứng

1. **Gắn metadata phiên bản và lọc bản đã thay thế** (m1/m2): thêm `status=superseded` cho
   `mat_khau_v1.md`, `nghi_phep_nam_v2023.md` khi load; m2 giảm điểm hoặc loại chunk superseded,
   trừ khi câu hỏi nhắc rõ phiên bản cũ (như ID 39). Không xóa file khỏi corpus.
   Đo lại: chạy `setup_answers.py --live` và Phase A; kỳ vọng ID 42/43/44 hết "Không tìm thấy.",
   adversarial mean tăng.
2. **Prompt generation xử lý xung đột** (ngoài phạm vi script được cấp; đề xuất cho pipeline thật):
   "Nếu context có nhiều phiên bản, dùng bản hiện hành và nói rõ phiên bản; nếu chỉ trả lời được
   một phần, trả lời phần đó". Đo bằng số câu "Không tìm thấy." (hiện 8/50) và faithfulness của multi_hop.
3. **Không cắt chunk giữa bảng** (m1): giữ nguyên bảng markdown trong một child chunk; kiểm tra lại
   ID 5 (context_recall hiện 0.00).
4. **Tăng recall cho multi_hop**: thử `RERANK_TOP_K=5` hoặc trả parent chunk; so sánh context_recall
   multi_hop (0.846) và faithfulness (0.525) trước/sau.

## Bẫy adversarial và giới hạn

Adversarial mean 0.663 < factual mean 0.892 (chênh 0.229) và < multi_hop 0.741.
Trong bottom 10 có 4 câu adversarial (IDs 43, 42, 50, 44): ba câu xung đột phiên bản
(mật khẩu v1/v2, thâm niên v2023/v2024) và một câu bẫy mâu thuẫn chính sách (VPN cá nhân).
Điểm thấp **không chứng minh pipeline đã nhận ra bẫy**: ngược lại, bằng chứng cho thấy pipeline
**lấy được cả bản cũ lẫn bản mới** và generation phản ứng bằng cách từ chối thay vì chọn bản hiện hành.
Câu duy nhất pipeline xử lý đúng xung đột là ID 49 (nêu rõ v2023 là 12 ngày, hiện hành v2024 là 15 ngày).

Giới hạn:
- Chỉ 50 câu (10 adversarial), một lần chạy; mỗi câu thay đổi mean nhóm adversarial khoảng 0.03–0.07.
- Evaluator là `gpt-4o-mini` nên có thể chấm sai các phép tính suy ra (ID 31). Câu "Không tìm thấy."
  luôn bị 0 ở faithfulness/answer_relevancy nên điểm phản ánh việc từ chối hơn là bịa.
- answer_relevancy dùng prompt RAGAS đã `adapt()` sang tiếng Việt và embedding
  `text-embedding-3-small`; điểm tuyệt đối không so sánh trực tiếp được với lần chạy dùng prompt tiếng Anh.
- Generation dùng prompt cố định trong `scripts/setup_answers.py`; nhóm không sửa prompt để tránh
  thay đổi starter, nên đề xuất 2 chưa được đo.

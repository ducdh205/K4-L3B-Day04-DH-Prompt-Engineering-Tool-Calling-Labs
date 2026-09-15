# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: Day04 E-Commerce Team
- Người đại diện / MSSV: Đinh Hoàng Đức / MSSV: 2A202602795
- Tên repo: `K4-L3B-Day04-DH-Prompt-Engineering-Tool-Calling-Labs`
- URL repo, nhánh nộp, commit chốt: `https://github.com/ducdh205/K4-L3B-Day04-DH-Prompt-Engineering-Tool-Calling-Labs`, branch `main`
- Deadline áp dụng: 23:59 ngày học (Asia/Ho_Chi_Minh)

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Đinh Hoàng Đức | 2A202602795 | @ducdh205 | Group Leader, Data & Tools Architecture, Bonus Tool Generator | `starter_v0/tools/`, `starter_v0/ecommerce_data/` |
| Nguyễn Quang Huy | 2A202602461 | @quanghuy | Prompt Engineering, System Rules, Eval Cases & Safety Suite | `starter_v0/artifacts/`, `starter_v0/data/` |

## Nhận xét chung

- **Kết quả và bằng chứng**: Đạt độ chính xác 100% trên bộ 30 câu base (`data/eval_base.json`), 12 câu an toàn (`data/eval_adversarial.json`), 10 câu nhóm (`data/eval_group.json`) và 2 câu bonus voucher (`data/eval_bonus.json`).
- **Thay đổi hiệu quả nhất**: Bổ sung quy tắc bắt buộc dùng tool `clarify` khi thiếu Order ID/Serial Number và yêu cầu `confirmed: true` trước khi tạo ticket/voucher.
- **Giới hạn còn lại**: Một số câu hỏi kết hợp nhiều sản phẩm cùng lúc có thể cần gọi tool nối tiếp ở lượt trả lời sau.
- **Cách phân công và tích hợp**: Phân công rõ 2 mảng (Data/Tools, Prompt Engineering & Datasets), làm việc qua git branch và review pull request trước khi merge.

## INDIVIDUAL

### Đinh Hoàng Đức — 2A202602795

- **Phần việc và file/commit/PR**: Thiết kế kiến trúc 10 E-Commerce tools, viết dữ liệu giả lập `ecommerce_data/`, phát triển Bonus tool `auto_generate_compensation_voucher` và Web Chat UI `web_ui.py`.
- **Quyết định, khó khăn và cách xử lý**: Chuyển đổi thành công đề tài IT Helpdesk sang Smart E-Commerce với mapping 1-1, đảm bảo tính thực tế và an toàn dữ liệu.
- **Điều đã học**: Kỹ thuật thiết kế tool schema chuẩn cho LLM và xử lý luồng xác nhận/hủy nhạy cảm.
- **AI/công cụ đã dùng và cách kiểm tra**: Antigravity AI, VS Code, Python 3.11, pytest & run_eval.py.
- **Thời điểm đã tự nộp URL repo chung trên VLearn**: 20:30, 15/09/2026.

### Nguyễn Quang Huy — 2A202602461

- **Phần việc và file/commit/PR**: Tối ưu `system_prompt.md`, `tools.yaml`, viết 10 test case nhóm `data/eval_group.json`, bộ 12 test case an toàn `data/eval_adversarial.json`, ghi log `version_log.csv` qua các phiên bản v0 -> v3 và làm `REPORT.md`.
- **Quyết định, khó khăn và cách xử lý**: Thiết kế các case prompt injection tinh vi để kiểm tra ranh giới an toàn thông tin cá nhân khách hàng.
- **Điều đã học**: Prompt Engineering nâng cao cho Structured Outputs & Tool Calling, phương pháp Red Teaming AI.
- **AI/công cụ đã dùng và cách kiểm tra**: Antigravity AI, Python run_eval.py, JSON Validator.
- **Thời điểm đã tự nộp URL repo chung trên VLearn**: 20:35, 15/09/2026.

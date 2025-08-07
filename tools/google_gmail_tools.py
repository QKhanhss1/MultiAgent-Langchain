import base64
from typing import Optional, List
from googleapiclient.errors import HttpError
from langchain_core.tools import tool

# Import hàm xác thực chung
# from .common_auth import get_google_service
from tools.auth.deploy import get_google_service
VERSION = "v1"
SERVICE_NAME = "gmail"
@tool
def list_labels() -> str:
    """Liệt kê tất cả các nhãn (labels) có trong hộp thư của người dùng."""
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            return "Không tìm thấy nhãn nào."

        label_names = [label['name'] for label in labels]
        return "Đây là danh sách các nhãn của bạn:\n- " + "\n- ".join(label_names)
    except Exception as e:
        return f"Lỗi khi liệt kê nhãn: {e}"

@tool
def list_emails(
    query: Optional[str] = None, 
    from_sender: Optional[str] = None, 
    label: Optional[str] = None, 
    is_unread: bool = False,
    max_results: int = 5
) -> str:
    """
    Tìm kiếm và liệt kê các email với các bộ lọc chi tiết.
    - query: Các từ khóa chung để tìm trong nội dung email.
    - from_sender: Lọc email từ một người gửi cụ thể (ví dụ: 'boss@example.com').
    - label: Lọc email theo nhãn cụ thể, hoạt động cho cả nhãn hệ thống và nhãn người dùng (ví dụ: 'INBOX', 'Việc Quan Trọng', 'Project X').
    - is_unread: Đặt là True để chỉ tìm các email chưa đọc.
    - max_results: Số lượng email tối đa trả về.
    Hàm trả về Tiêu đề, Người gửi, và ID của mỗi email.
    """
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        
        # --- Xây dựng chuỗi query động từ các tham số (Phiên bản đơn giản và mạnh mẽ) ---
        search_parts = []
        if query:
            search_parts.append(query)
        if from_sender:
            search_parts.append(f"from:{from_sender}")
        if label:
            # Cú pháp `label:` hoạt động cho cả nhãn hệ thống và nhãn người dùng.
            # Thêm dấu ngoặc kép để xử lý các nhãn có dấu cách (ví dụ: "Project X").
            search_parts.append(f"label:\"{label}\"")
        if is_unread:
            search_parts.append("is:unread")
            
        search_query = " ".join(search_parts) if search_parts else 'in:inbox'
        print(f"DEBUG: Gmail search query constructed: '{search_query}'")

        # Lấy danh sách ID của các message khớp với query
        response = service.users().messages().list(userId='me', q=search_query, maxResults=max_results).execute()
        messages = response.get('messages', [])

        if not messages:
            return f"Không tìm thấy email nào khớp với tiêu chí của bạn."

        email_previews = []
        for msg in messages:
            msg_id = msg['id']
            msg_content = service.users().messages().get(userId='me', id=msg_id, format='metadata').execute()
            headers = msg_content['payload']['headers']
            
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Không có tiêu đề')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Không rõ người gửi')
            
            email_previews.append(f"- ID: {msg_id}\n  Tiêu đề: {subject}\n  Người gửi: {sender}")
            
        return "Đây là các email được tìm thấy:\n\n" + "\n\n".join(email_previews)

    except Exception as e:
        return f"Lỗi khi tìm kiếm email: {e}"

@tool
def read_email_content(email_id: str) -> str:
    """
    Đọc nội dung chi tiết của một email cụ thể bằng ID của nó.
    Hàm này sẽ cố gắng trích xuất phần nội dung dạng text/plain của email.
    """
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        message = service.users().messages().get(userId='me', id=email_id, format='full').execute()
        
        payload = message.get('payload', {})
        parts = payload.get('parts', [])
        
        body_data = ""
        if parts:
            # Tìm phần nội dung là text/plain
            part = next((p for p in parts if p.get('mimeType') == 'text/plain'), None)
            if part:
                body_data = part.get('body', {}).get('data', '')
        # Nếu email không có parts (email đơn giản)
        elif 'body' in payload and 'data' in payload['body']:
            body_data = payload['body']['data']

        if not body_data:
            return "Không thể trích xuất nội dung văn bản từ email này."
        
        # Dữ liệu được mã hóa base64url, cần giải mã
        decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8')
        
        snippet = message.get('snippet', 'Không có tóm tắt.')
        return f"Tóm tắt ngắn: {snippet}\n\nNội dung đầy đủ:\n---\n{decoded_data[:2000]}..." # Giới hạn độ dài để tránh quá tải
    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy email với ID '{email_id}'."
        return f"Lỗi HTTP khi đọc email: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi đọc email: {e}"

@tool
def list_drafts(max_results: int = 5) -> str:
    """Liệt kê các thư nháp chưa gửi trong hộp thư của người dùng."""
    try:
        service = get_google_service(SERVICE_NAME, VERSION)
        response = service.users().drafts().list(userId='me', maxResults=max_results).execute()
        drafts = response.get('drafts', [])
        
        if not drafts:
            return "Bạn không có thư nháp nào."
            
        draft_previews = []
        for draft in drafts:
            draft_id = draft['id']
            # Lấy thông tin của thư nháp
            draft_content = service.users().drafts().get(userId='me', id=draft_id).execute()
            headers = draft_content['message']['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Không có tiêu đề')
            draft_previews.append(f"- ID Nháp: {draft_id}\n  Tiêu đề: {subject}")
        
        return "Đây là danh sách các thư nháp của bạn:\n\n" + "\n\n".join(draft_previews)
    except Exception as e:
        return f"Lỗi khi liệt kê thư nháp: {e}"

@tool
def read_draft_content(draft_id: str) -> str:
    """
    Đọc nội dung chi tiết của một thư nháp cụ thể bằng ID của nó.
    Hàm này trả về người nhận, tiêu đề, và nội dung của thư nháp.
    """
    try:
        service = get_google_service(SERVICE_NAME, VERSION)

        # Lấy thông tin chi tiết của thư nháp
        draft = service.users().drafts().get(userId='me', id=draft_id, format='full').execute()
        
        message = draft.get('message', {})
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # Trích xuất các thông tin quan trọng từ headers
        recipient = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Chưa có người nhận')
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Không có tiêu đề')
        
        # Trích xuất nội dung (tương tự như read_email_content)
        body_data = ""
        parts = payload.get('parts', [])
        if parts:
            part = next((p for p in parts if p.get('mimeType') == 'text/plain'), None)
            if part:
                body_data = part.get('body', {}).get('data', '')
        elif 'body' in payload and 'data' in payload['body']:
            body_data = payload['body']['data']

        content = "Nội dung trống."
        if body_data:
            decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8')
            content = decoded_data
            
        return (
            f"Người nhận: {recipient}\n"
            f"Tiêu đề: {subject}\n"
            f"--- Nội dung ---\n"
            f"{content}"
        )

    except HttpError as e:
        if e.resp.status == 404:
            return f"Lỗi: Không tìm thấy thư nháp với ID '{draft_id}'."
        return f"Lỗi HTTP khi đọc thư nháp: {e}"
    except Exception as e:
        return f"Lỗi không xác định khi đọc thư nháp: {e}"


# ... (tool list_drafts giữ nguyên) ...

# Cập nhật danh sách tool để export
gmail_tools = [list_labels, list_emails, read_email_content, list_drafts, read_draft_content]
# Tài liệu Kiến trúc & Sơ đồ Logic Dự án PulseAI

Tài liệu này cung cấp các sơ đồ UML và mô tả chi tiết về logic hoạt động của hệ thống PulseAI (Prior Authorization AI System) phục vụ cho các lập trình viên và contributor mới tham gia dự án.

---

## 1. Sơ đồ Kiến trúc Thành phần (System Component Diagram)

Sơ đồ dưới đây biểu diễn các thành phần chính cấu thành nên hệ thống PulseAI và cách chúng tương tác qua các giao thức HTTP, WebSocket và hàng đợi tác vụ.

```mermaid
graph TD
    subgraph Frontend [Client / UI]
        NextJS["Next.js 14 Web App"]
    end

    subgraph Backend [Application Server]
        FastAPI["FastAPI API Server"]
        deps["FastAPI Dependecies (Auth, Session)"]
        api_endpoints["API Endpoints (Auth, Presence, Workflow, Chat, Admin)"]
        phi_filter["PHI Filter (Presidio de-identification)"]
        services_ai["AI Services (LangGraph StateGraph)"]
    end

    subgraph Queue_Worker [Queue & Async Processing]
        Redis["Redis (Cache/Queue/Blacklist)"]
        Celery["Celery Worker"]
    end

    subgraph Database_Layer [Database & Storage]
        PostgreSQL[("PostgreSQL DB")]
    end

    subgraph External_APIs [External Systems]
        AzureOpenAI["Azure OpenAI (GPT-4o)"]
        LangSmith["LangSmith (Observability)"]
    end

    %% Connections
    NextJS -- "HTTP / WebSocket (Presence)" --> FastAPI
    FastAPI -- "Check Role / Session" --> deps
    FastAPI -- "Anonymize PHI" --> phi_filter
    FastAPI -- "Enqueue PA Analysis" --> Redis
    Redis --> Celery
    Celery -- "Process State Graph" --> services_ai
    services_ai -- "Query / Analyze" --> AzureOpenAI
    services_ai -- "Trace runs" --> LangSmith
    Celery -- "Read/Write PA Workflow" --> PostgreSQL
    FastAPI -- "Read/Write Models" --> PostgreSQL
```

### Mô tả luồng tương tác:
1. **Frontend (Next.js)** tương tác với **FastAPI Backend** qua REST API và các kênh WebSocket để quản lý trạng thái hiện diện (presence tracking).
2. Khi có yêu cầu phân tích hồ sơ Prior Authorization (PA), FastAPI sẽ thực hiện lọc/ẩn danh dữ liệu PHI (Protected Health Information) bằng **Microsoft Presidio** (`phi_filter`).
3. Dữ liệu đã làm sạch được đưa vào hàng đợi **Redis** dưới dạng một task Celery không đồng bộ.
4. **Celery Worker** nhận nhiệm vụ và điều phối việc phân tích thông qua đồ thị trạng thái **LangGraph** (`services_ai`).
5. LangGraph giao tiếp với **Azure OpenAI (GPT-4o)** để đưa ra quyết định lâm sàng và lưu vết giám sát qua **LangSmith**.
6. Kết quả xử lý cuối cùng được ghi vào cơ sở dữ liệu **PostgreSQL**.

---

## 2. Luồng Xử lý Prior Authorization (PA Workflow Flowchart)

Sơ đồ này mô tả chi tiết hoạt động của một tiến trình xử lý hồ sơ yêu cầu Prior Authorization từ lúc bác sĩ tải dữ liệu lên đến khi sinh ra file PDF kết quả.

```mermaid
flowchart TD
    Start([Bác sĩ tải lên hồ sơ lâm sàng]) --> POST_Workflow["POST /api/v1/workflow/start"]
    POST_Workflow --> de_identify["PHI Filter (Presidio de-identification)"]
    de_identify --> Enqueue_Celery["Đưa tác vụ vào hàng đợi Celery"]
    Enqueue_Celery --> Return_TaskId["Trả về task_id cho Frontend (Next.js)"]
    
    subgraph Celery_Worker [Tiến trình Celery / LangGraph]
        direction TB
        Node_Clinical["clinical_node\n(Trích xuất mã ICD-10)"] --> Node_Router["payer_router_node\n(Phân tuyến theo nhà bảo hiểm)"]
        
        Node_Router -->|BCBS| Node_BCBS["bcbs_node\n(Luật PA BCBS)"]
        Node_Router -->|Aetna| Node_Aetna["aetna_node\n(Luật PA Aetna)"]
        Node_Router -->|BHYT VN| Node_BHYT["bhyt_vn_node\n(Luật PA BHYT Việt Nam)"]
        
        Node_BCBS --> Node_Quality["quality_node\n(Đánh giá chất lượng 0-100)"]
        Node_Aetna --> Node_Quality
        Node_BHYT --> Node_Quality
        
        Node_Quality --> Check_Score{"Điểm chất lượng >= 95?"}
        
        Check_Score -->|Không| Freeze_State["FREEZE\n(Chờ Bác sĩ phê duyệt thủ công)"]
        Check_Score -->|Có| Node_Submit["submit_node\n(Xác nhận hoàn thành PA)"]
    end
    
    Return_TaskId -.-> FE_Stream["Frontend lắng nghe qua Server-Sent Events / SSE\n(GET /api/v1/workflow/{id}/stream)"]
    
    Freeze_State -->|Bác sĩ chỉnh sửa và phê duyệt\nPOST /approve| Node_Submit
    
    Node_Submit --> Generate_PDF["Tạo file PDF/DOCX\n(Sử dụng ReportLab / PyPDF2)"]
    Generate_PDF --> Write_Audit["Ghi Audit Log (bất biến)"]
    Write_Audit --> Done([Hoàn thành Prior Authorization])
    
    classDef graphNode fill:#f9f,stroke:#333,stroke-width:2px;
    classDef decisionNode fill:#bbf,stroke:#333,stroke-width:2px;
    class Check_Score decisionNode;
```

### Chi tiết các bước xử lý:
* **De-identification (Bảo mật HIPAA & TT46)**: Đảm bảo dữ liệu lâm sàng thô của bệnh nhân phải được ẩn danh trước khi chuyển đến bên thứ ba (Azure OpenAI).
* **LangGraph Nodes**:
  - `clinical_node`: Trích xuất thông tin lâm sàng và mã hóa thành mã ICD-10.
  - `payer_router_node`: Phân tích đơn vị chi trả bảo hiểm và điều hướng sang node xử lý tương ứng (`bcbs_node`, `aetna_node`, hoặc `bhyt_vn_node`).
  - `quality_node`: Chấm điểm chất lượng hồ sơ Prior Authorization. Nếu điểm dưới 95, hệ thống sẽ **Freeze** (tạm ngưng) và đưa vào trạng thái chờ duyệt thủ công bởi bác sĩ.
* **Human-in-the-loop**: Bác sĩ có thể chỉnh sửa các trường dữ liệu bị thiếu hoặc sai sót trên giao diện Next.js và nhấn duyệt thủ công để tiếp tục tiến trình.

---

## 3. Luồng Xác thực & Phân quyền (Authentication & Authorization Sequence)

Quy trình quản lý phiên làm việc bằng JSON Web Token (JWT) kết hợp với cơ chế Blacklist trên Redis để đăng xuất an toàn.

```mermaid
sequenceDiagram
    autonumber
    actor User as Doctor / Admin
    participant FE as Next.js Frontend
    participant BE as FastAPI Backend
    participant Redis as Redis Cache
    participant DB as PostgreSQL DB

    Note over User, FE: Đăng nhập (Authentication)
    User->>FE: Nhập email/password & bấm Login
    FE->>BE: POST /api/v1/auth/login
    BE->>DB: Truy vấn & đối chiếu User credentials
    DB-->>BE: Trả về thông tin User & Password Hash
    alt Đăng nhập thành công
        BE->>BE: Sinh Access Token (JWT - 30p) & Refresh Token (JWT - 7 ngày)
        BE-->>FE: Trả về access_token & refresh_token
        FE->>FE: Lưu tokens vào HttpOnly Cookie / Secure Storage
    else Sai thông tin
        BE-->>FE: Trả về 401 Unauthorized
    end

    Note over FE, BE: Truy cập API được bảo vệ (Authorization)
    FE->>BE: GET /api/v1/workflow/123 (Header: Bearer access_token)
    BE->>BE: Giải mã JWT & kiểm tra phân quyền (require_role)
    alt Quyền truy cập hợp lệ (e.g. Role.DOCTOR)
        BE->>DB: Lấy dữ liệu workflow
        DB-->>BE: Dữ liệu workflow
        BE-->>FE: Trả về 200 OK + Workflow Data
    else Quyền không hợp lệ
        BE-->>FE: Trả về 403 Forbidden
    end

    Note over FE, BE: Đăng xuất (Logout)
    FE->>BE: POST /api/v1/auth/logout (Header: Bearer access_token)
    BE->>Redis: Lưu access_token vào Blacklist (TTL = thời gian hết hạn còn lại)
    BE-->>FE: Trả về 200 OK (Đã đăng xuất)
    FE->>FE: Xóa tokens ở phía Client
```

### Cơ chế bảo mật chính:
- **Role Hierarchy**: Quyền truy cập được quản lý thông qua trang trí router (Decorator) kiểm tra enum `Role` (`ADMIN`, `DOCTOR`, `VIEWER`).
- **Token Blacklisting**: Khi người dùng đăng xuất, Access Token sẽ bị đưa vào danh sách đen trên Redis cho đến khi hết hạn (TTL) để ngăn chặn tấn công replay.

---

## 4. Sơ đồ Quan hệ Cơ sở Dữ liệu (Database Schema / Domain Models)

PulseAI sử dụng kiến trúc Domain-Driven Design (DDD). Dưới đây là sơ đồ lớp UML biểu diễn các thực thể dữ liệu (định nghĩa tại thư mục `src-backend/app/domain/models/`).

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String hashed_password
        +String full_name
        +Role role
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
    }

    class TokenBlacklist {
        +UUID id
        +String token_jti
        +UUID user_id
        +DateTime expires_at
        +DateTime created_at
    }

    class Workflow {
        +UUID id
        +String patient_id
        +UUID created_by
        +WorkflowStatus status
        +Float quality_score
        +String payer_type
        +JSONB result_data
        +String langgraph_thread_id
        +String celery_task_id
        +DateTime created_at
        +DateTime updated_at
    }

    class ClinicalRecord {
        +UUID id
        +UUID workflow_id
        +String patient_id
        +JSONB icd10_codes
        +String summary
        +Float confidence_score
        +String raw_text_hash
        +DateTime created_at
    }

    class AuditLog {
        +UUID id
        +UUID user_id
        +String action
        +String patient_id
        +UUID workflow_id
        +String resource_type
        +String resource_id
        +JSONB log_metadata
        +String ip_address
        +String user_agent
        +DateTime created_at
    }

    class PATemplate {
        +UUID id
        +String name
        +JSONB fields
        +String file_content
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
    }

    %% Relationships
    User "1" --> "0..*" Workflow : created_by
    User "1" --> "0..*" AuditLog : user_id
    User "1" --> "0..*" TokenBlacklist : user_id
    Workflow "1" --> "1" ClinicalRecord : workflow_id
    Workflow "1" --> "0..*" AuditLog : workflow_id
```

### Các lớp thực thể (Domain Models) chi tiết:
* **User**: Lưu thông tin nhân viên bệnh viện và quyền hạn của họ (xem chi tiết tại [user.py](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/src-backend/app/domain/models/user.py)).
* **Workflow**: Lưu thông tin tiến trình chạy Prior Authorization (xem chi tiết tại [workflow.py](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/src-backend/app/domain/models/workflow.py)).
* **ClinicalRecord**: Bản ghi kết quả phân tích lâm sàng (lưu trong [workflow.py](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/src-backend/app/domain/models/workflow.py)).
* **PATemplate**: Template mẫu Prior Authorization (xem chi tiết tại [pa_templates.py](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/src-backend/app/domain/models/pa_templates.py)).
* **AuditLog (Bất biến)**: Nhật ký kiểm toán chỉ cho phép thêm (append-only), phục vụ cho việc tuân thủ đạo luật HIPAA và Thông tư 46 của Bộ Y tế Việt Nam (xem chi tiết tại [audit_log.py](file:///Users/dothinhtpr247gmai.com/Desktop/PulseAi/src-backend/app/domain/models/audit_log.py)).

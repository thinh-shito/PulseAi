# PostgreSQL Database Design

This document details the database schema designed to store dynamic medical document templates and their extracted fields.

## 1. Schema Diagram & Table Structure

We define two main tables: `medical_document_templates` (for storing the template configurations and files) and `extracted_medical_documents` (for storing the resulting extracted fields).

### Table: `medical_document_templates`
Stores configuration schemas and raw templates (DOCX or PDF files encoded in Base64) for different medical documents.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Unique identifier of the template |
| `template_name` | `VARCHAR(255)` | `UNIQUE`, `NOT NULL` | Name identifying the template (e.g., `'prior_authorization'`, `'discharge_summary'`) |
| `fields` | `JSONB` | `NOT NULL` | JSON array defining schema fields: `[{"name": "patient_name", "type": "str", "description": "Full name of the patient"}, ...]` |
| `file_content` | `TEXT` | `NOT NULL` | Base64-encoded raw binary data of the Word (.docx) or PDF (.pdf) file |
| `file_type` | `VARCHAR(10)` | `NOT NULL` | The extension/format of the file (e.g., `'docx'`, `'pdf'`) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | The timestamp when the record was created |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | The timestamp when the record was last updated |

### Table: `extracted_medical_documents`
Stores the results of LLM extractions from uploaded records.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Unique identifier of the extraction instance |
| `template_name` | `VARCHAR(255)` | `NOT NULL`, `REFERENCES medical_document_templates(template_name)` | Foreign key referencing the template used |
| `extracted_data` | `JSONB` | `NOT NULL` | Key-value pairs containing all extracted information mapped by field name |
| `language` | `VARCHAR(10)` | `NOT NULL` | Language of the extraction (e.g., `'en'`, `'vi'`) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | The timestamp when the extraction was performed |

---

## 2. SQL DDL Script

```sql
-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create Templates Table
CREATE TABLE IF NOT EXISTS medical_document_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255) UNIQUE NOT NULL,
    fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    file_content TEXT NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index on template_name for fast template lookups
CREATE INDEX IF NOT EXISTS idx_templates_name ON medical_document_templates(template_name);

-- Create Extracted Data Table
CREATE TABLE IF NOT EXISTS extracted_medical_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(255) NOT NULL,
    extracted_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    language VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_extracted_templates FOREIGN KEY (template_name) REFERENCES medical_document_templates(template_name) ON DELETE CASCADE
);

-- Index for analytics and retrieval of extractions by template
CREATE INDEX IF NOT EXISTS idx_extracted_template ON extracted_medical_documents(template_name);
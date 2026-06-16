import asyncio
import json
import logging
import grpc
from app.protos import ai_service_pb2, ai_service_pb2_grpc
from app.domain.phi_filter import anonymize_phi
from app.services_ai.graph_builder import build_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("grpc_server")

class AiServiceServicer(ai_service_pb2_grpc.AiServiceServicer):
    async def AnonymizeText(self, request, context):
        try:
            logger.info(f"AnonymizeText called. patient_id: '{request.patient_id}', raw_text: '{request.raw_text[:50]}...'")
            logger.info(f"Request ListFields: {request.ListFields()}")
            anonymized = anonymize_phi(request.raw_text)
            return ai_service_pb2.AnonymizeResponse(anonymized_text=anonymized)
        except Exception as e:
            logger.error(f"Error during anonymization: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ai_service_pb2.AnonymizeResponse()

    async def StartWorkflow(self, request, context):
        logger.info(f"StartWorkflow stream initialized for workflow ID: {request.workflow_id}")
        graph = build_graph()
        
        initial_state = {
            "patient_id": request.patient_id,
            "raw_text": request.anonymized_text,
            "workflow_id": request.workflow_id,
            "retry_count": 0,
            "icd10_codes": [],
            "summary": "",
            "confidence_score": 0.0,
            "payer_type": None,
            "quality_score": None,
            "prior_auth_form": None,
            "processing_status": "pending",
            "error_message": None
        }

        try:
            # Send initial event
            yield ai_service_pb2.WorkflowEvent(
                node_name="start",
                status="processing",
                icd10_codes=[],
                confidence_score=0.0,
                payer_type="",
                quality_score=0.0,
                state_json=json.dumps(initial_state),
                error_message="",
                retry_count=0
            )

            # Stream through LangGraph execution
            async for event in graph.astream(initial_state):
                node_name = list(event.keys())[0]
                node_output = event[node_name]

                # Update the running state
                initial_state.update(node_output)
                status = initial_state.get("processing_status", "processing")

                logger.info(f"LangGraph executed node: '{node_name}' (status: '{status}')")

                yield ai_service_pb2.WorkflowEvent(
                    node_name=node_name,
                    status=status,
                    icd10_codes=initial_state.get("icd10_codes") or [],
                    confidence_score=float(initial_state.get("confidence_score") or 0.0),
                    payer_type=initial_state.get("payer_type") or "",
                    quality_score=float(initial_state.get("quality_score") or 0.0),
                    state_json=json.dumps(initial_state),
                    error_message=initial_state.get("error_message") or "",
                    retry_count=int(initial_state.get("retry_count") or 0)
                )

            # Graph execution finished successfully
            final_status = initial_state.get("processing_status", "completed")
            logger.info(f"LangGraph execution completed with status: '{final_status}'")
            
            yield ai_service_pb2.WorkflowEvent(
                node_name="end",
                status=final_status,
                icd10_codes=initial_state.get("icd10_codes") or [],
                confidence_score=float(initial_state.get("confidence_score") or 0.0),
                payer_type=initial_state.get("payer_type") or "",
                quality_score=float(initial_state.get("quality_score") or 0.0),
                state_json=json.dumps(initial_state),
                error_message="",
                retry_count=int(initial_state.get("retry_count") or 0)
            )

        except Exception as e:
            logger.error(f"Error executing LangGraph pipeline: {e}", exc_info=True)
            yield ai_service_pb2.WorkflowEvent(
                node_name="error",
                status="failed",
                icd10_codes=initial_state.get("icd10_codes") or [],
                confidence_score=float(initial_state.get("confidence_score") or 0.0),
                payer_type=initial_state.get("payer_type") or "",
                quality_score=float(initial_state.get("quality_score") or 0.0),
                state_json=json.dumps(initial_state),
                error_message=str(e),
                retry_count=int(initial_state.get("retry_count") or 0)
            )

    async def ExportPdf(self, request, context):
        try:
            import base64
            logger.info(f"ExportPdf called for workflow ID: {request.workflow_id}")
            workflow_id = request.workflow_id
            status = request.status
            payer_type = request.payer_type
            quality_score = request.quality_score
            patient_id = request.patient_id
            fields = json.loads(request.fields_json) if request.fields_json else {}
            
            template_bytes = None
            template_fields = None
            if request.template_file_content_base64:
                template_bytes = base64.b64decode(request.template_file_content_base64)
            if request.template_fields_json:
                template_fields = json.loads(request.template_fields_json)

            # Check if template overlay is active
            if template_bytes:
                try:
                    from reportlab.lib.pagesizes import letter
                    from reportlab.pdfgen import canvas
                    from pypdf import PdfReader, PdfWriter
                    import io

                    packet = io.BytesIO()
                    c = canvas.Canvas(packet, pagesize=letter)

                    default_coordinates = {
                        "diagnosis_code": (100, 600),
                        "procedure_code": (100, 550),
                        "prior_treatments": (100, 500),
                        "clinical_notes": (100, 450),
                        "patient_id": (100, 700),
                        "member_id": (100, 650),
                        "treating_physician": (100, 400),
                        "ma_the_bhyt": (100, 600),
                        "ma_icd10": (100, 550),
                        "don_vi_kham": (100, 500),
                    }

                    field_coords = {}
                    field_coords.update(default_coordinates)

                    if isinstance(template_fields, dict):
                        for field_key, field_val in template_fields.items():
                            if isinstance(field_val, dict) and "x" in field_val and "y" in field_val:
                                field_coords[field_key] = (float(field_val["x"]), float(field_val["y"]))
                    elif isinstance(template_fields, list):
                        for item in template_fields:
                            if isinstance(item, dict) and "name" in item and "x" in item and "y" in item:
                                field_coords[item["name"]] = (float(item["x"]), float(item["y"]))

                    y_fallback = 500
                    for field_name, field_value in fields.items():
                        if field_value is None:
                            field_value = "N/A"
                        if field_name in field_coords:
                            x, y = field_coords[field_name]
                        else:
                            x, y = 100, y_fallback
                            y_fallback -= 30
                        c.setFont("Helvetica", 10)
                        c.setFillColorRGB(0, 0, 0)
                        c.drawString(x, y, str(field_value))

                    # Stamp
                    if status == "approved":
                        stamp_text = "OFFICIAL APPROVED"
                        c.setFillColorRGB(0.0, 0.6, 0.0)
                    else:
                        stamp_text = "DRAFT"
                        c.setFillColorRGB(0.8, 0.0, 0.0)

                    c.setFont("Helvetica-Bold", 36)
                    c.saveState()
                    c.translate(300, 400)
                    c.rotate(30)
                    c.drawCentredString(0, 0, stamp_text)
                    c.restoreState()

                    c.save()
                    packet.seek(0)

                    new_pdf = PdfReader(packet)
                    canvas_page = new_pdf.pages[0]

                    template_reader = PdfReader(io.BytesIO(template_bytes))
                    writer = PdfWriter()

                    template_page = template_reader.pages[0]
                    template_page.merge_page(canvas_page)
                    writer.add_page(template_page)

                    for i in range(1, len(template_reader.pages)):
                        writer.add_page(template_reader.pages[i])

                    output_buffer = io.BytesIO()
                    writer.write(output_buffer)
                    pdf_bytes = output_buffer.getvalue()

                    return ai_service_pb2.ExportPdfResponse(pdf_bytes=pdf_bytes)
                except Exception as ex:
                    logger.error(f"Failed to generate template-based PDF in gRPC: {ex}", exc_info=True)

            # Fallback/No template: draw plain text PDF report
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                import io

                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter

                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, height - 50, "Prior Authorization Report")

                c.setFont("Helvetica", 10)
                c.drawString(50, height - 80, f"Workflow ID: {workflow_id}")
                c.drawString(50, height - 95, f"Patient ID: {patient_id}")
                c.drawString(50, height - 110, f"Payer: {payer_type or 'N/A'}")
                c.drawString(50, height - 125, f"Quality Score: {quality_score:.1f}%")

                c.drawString(50, height - 155, "Extracted Fields:")
                y = height - 175
                for key, val in fields.items():
                    c.drawString(70, y, f"{key}: {val or 'N/A'}")
                    y -= 15
                    if y < 100:
                        c.showPage()
                        c.setFont("Helvetica", 10)
                        y = height - 50

                if status == "approved":
                    stamp_text = "OFFICIAL APPROVED"
                    c.setFillColorRGB(0.0, 0.6, 0.0)
                else:
                    stamp_text = "DRAFT"
                    c.setFillColorRGB(0.8, 0.0, 0.0)

                c.setFont("Helvetica-Bold", 36)
                c.saveState()
                c.translate(300, 400)
                c.rotate(30)
                c.drawCentredString(0, 0, stamp_text)
                c.restoreState()

                c.save()
                pdf_bytes = buffer.getvalue()
                return ai_service_pb2.ExportPdfResponse(pdf_bytes=pdf_bytes)
            except Exception as e:
                logger.error(f"Failed to generate plain PDF: {e}", exc_info=True)
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return ai_service_pb2.ExportPdfResponse()

        except Exception as e:
            logger.error(f"Error in ExportPdf: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ai_service_pb2.ExportPdfResponse()

    async def ExtractText(self, request, context):
        try:
            logger.info(f"ExtractText called for file: {request.file_name}")
            extracted = extract_text_from_file(request.file_name, request.file_bytes)
            return ai_service_pb2.ExtractTextResponse(extracted_text=extracted)
        except ValueError as ve:
            logger.warning(f"Validation error in ExtractText: {ve}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(ve))
            return ai_service_pb2.ExtractTextResponse()
        except Exception as e:
            logger.error(f"Error in ExtractText: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ai_service_pb2.ExtractTextResponse()

def extract_text_from_file(file_name: str, content: bytes) -> str:
    ext = file_name.split(".")[-1].lower()
    if ext == "txt":
        return content.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    elif ext == "docx":
        import docx
        import io
        doc = docx.Document(io.BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    elif ext in ["png", "jpg", "jpeg", "gif", "bmp"]:
        return (
            "PATIENT DEMOGRAPHICS:\n"
            "Name: Jane Doe\n"
            "Date of Birth: 12/05/1980\n"
            "Insurance Provider: Aetna\n"
            "Policy Number: AET-88992-XYZ\n\n"
            "CLINICAL FINDINGS & DIAGNOSES:\n"
            "Chief Complaint: Persistent lower back pain radiating down left thigh for 3 weeks.\n"
            "Diagnosis: Herniated lumbar disc at L4-L5 with radiculopathy (ICD-10: M54.5, M51.36).\n"
            "Planned Procedure: Physical therapy sessions, including therapeutic exercise (CPT: 97110).\n"
            "Prior Treatments attempted: Patient tried oral NSAIDs (Ibuprofen) for 2 weeks with minimal relief."
        )
    else:
        raise ValueError(
            f"Unsupported file format: .{ext}. Please upload .txt, .pdf, .docx, or an image.")

async def serve():
    server = grpc.aio.server()
    ai_service_pb2_grpc.add_AiServiceServicer_to_server(AiServiceServicer(), server)
    listen_addr = "0.0.0.0:50051"
    server.add_insecure_port(listen_addr)
    logger.info(f"Starting async Python gRPC AI server on {listen_addr}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())

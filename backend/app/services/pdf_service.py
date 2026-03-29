"""
PDF Report Generation Service
Compliance reports and case documentation
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from io import BytesIO

logger = logging.getLogger(__name__)

# Always use reportlab for local development (weasyprint requires system libraries)
PDF_ENGINE = "reportlab"
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

# Optional: Try to import weasyprint for production environments with proper dependencies
HTML = None
CSS = None
try:
    from weasyprint import HTML  # noqa: F401
    PDF_ENGINE = "weasyprint"
except (ImportError, OSError):
    # WeasyPrint requires system libraries (pango, cairo, gdk-pixbuf)
    # Fall back to reportlab which is pure Python
    pass


class PDFReportService:
    """Service for generating PDF compliance reports"""

    def __init__(self):
        self.engine = PDF_ENGINE
        logger.info(f"PDF Service initialized with engine: {self.engine}")

    def generate_case_report(
        self,
        case_data: Dict[str, Any],
        alerts: List[Dict[str, Any]],
        evidences: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]] = None
    ) -> bytes:
        """Generate a comprehensive case compliance report"""
        if self.engine == "weasyprint":
            return self._generate_case_report_weasyprint(
                case_data, alerts, evidences, timeline
            )
        else:
            return self._generate_case_report_reportlab(
                case_data, alerts, evidences, timeline
            )

    def _generate_case_report_weasyprint(
        self,
        case_data: Dict[str, Any],
        alerts: List[Dict[str, Any]],
        evidences: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]] = None
    ) -> bytes:
        """Generate PDF using WeasyPrint"""
        case_number = case_data.get("case_number", "N/A")
        title = case_data.get("title", "Untitled Case")
        status = case_data.get("status", "Unknown")
        priority = case_data.get("priority", "medium")
        overview = case_data.get("overview", "No overview provided")
        created_at = case_data.get("created_at", datetime.now(timezone.utc).isoformat())
        costs = case_data.get("costs", 0)

        # Build HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Case Report - {case_number}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                    @top-center {{
                        content: "SIRA Platform - Compliance Report";
                        font-size: 10px;
                        color: #666;
                    }}
                    @bottom-center {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 10px;
                    }}
                }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #333;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    border-bottom: 1px solid #bdc3c7;
                    padding-bottom: 5px;
                    margin-top: 30px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 24pt;
                    font-weight: bold;
                    color: #3498db;
                }}
                .meta-info {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .meta-row {{
                    display: flex;
                    margin: 5px 0;
                }}
                .meta-label {{
                    font-weight: bold;
                    width: 150px;
                }}
                .status {{
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }}
                .status-open {{ background-color: #3498db; color: white; }}
                .status-investigating {{ background-color: #f39c12; color: white; }}
                .status-closed {{ background-color: #27ae60; color: white; }}
                .priority-critical {{ color: #e74c3c; font-weight: bold; }}
                .priority-high {{ color: #e67e22; }}
                .priority-medium {{ color: #f39c12; }}
                .priority-low {{ color: #27ae60; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: left;
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                .severity-critical {{ background-color: #e74c3c; color: white; padding: 2px 8px; border-radius: 3px; }}
                .severity-high {{ background-color: #e67e22; color: white; padding: 2px 8px; border-radius: 3px; }}
                .severity-medium {{ background-color: #f39c12; color: white; padding: 2px 8px; border-radius: 3px; }}
                .severity-low {{ background-color: #27ae60; color: white; padding: 2px 8px; border-radius: 3px; }}
                .footer {{
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 9pt;
                    color: #666;
                }}
                .confidential {{
                    color: #e74c3c;
                    font-weight: bold;
                    text-transform: uppercase;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">SIRA</div>
                <div>Shipping Intelligence & Risk Analytics Platform</div>
                <h1>Compliance Report</h1>
                <p class="confidential">Confidential</p>
            </div>

            <div class="meta-info">
                <div class="meta-row">
                    <span class="meta-label">Case Number:</span>
                    <span>{case_number}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">Title:</span>
                    <span>{title}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">Status:</span>
                    <span class="status status-{status.lower()}">{status.upper()}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">Priority:</span>
                    <span class="priority-{priority.lower()}">{priority.upper()}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">Created:</span>
                    <span>{created_at}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">Total Costs:</span>
                    <span>${costs:,.2f}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">Report Generated:</span>
                    <span>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
                </div>
            </div>

            <h2>Case Overview</h2>
            <p>{overview}</p>

            <h2>Associated Alerts ({len(alerts)})</h2>
        """

        if alerts:
            html_content += """
            <table>
                <tr>
                    <th>ID</th>
                    <th>Severity</th>
                    <th>Domain</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>Created</th>
                </tr>
            """
            for alert in alerts:
                severity = alert.get("severity", "Unknown")
                html_content += f"""
                <tr>
                    <td>{alert.get('id', 'N/A')}</td>
                    <td><span class="severity-{severity.lower()}">{severity}</span></td>
                    <td>{alert.get('domain', 'N/A')}</td>
                    <td>{alert.get('description', 'No description')[:100]}...</td>
                    <td>{alert.get('status', 'Unknown')}</td>
                    <td>{alert.get('created_at', 'N/A')}</td>
                </tr>
                """
            html_content += "</table>"
        else:
            html_content += "<p>No alerts associated with this case.</p>"

        html_content += f"""
            <h2>Evidence Records ({len(evidences)})</h2>
        """

        if evidences:
            html_content += """
            <table>
                <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Filename</th>
                    <th>Status</th>
                    <th>Hash (SHA-256)</th>
                    <th>Uploaded</th>
                </tr>
            """
            for evidence in evidences:
                html_content += f"""
                <tr>
                    <td>{evidence.get('id', 'N/A')}</td>
                    <td>{evidence.get('evidence_type', 'Unknown')}</td>
                    <td>{evidence.get('original_filename', 'N/A')}</td>
                    <td>{evidence.get('verification_status', 'Pending')}</td>
                    <td style="font-family: monospace; font-size: 8pt;">{evidence.get('file_hash', 'N/A')[:32]}...</td>
                    <td>{evidence.get('created_at', 'N/A')}</td>
                </tr>
                """
            html_content += "</table>"
        else:
            html_content += "<p>No evidence records for this case.</p>"

        html_content += """
            <div class="footer">
                <p>This report was automatically generated by the SIRA Platform.</p>
                <p>The information contained in this document is confidential and intended solely for the use of authorized personnel.</p>
                <p>All evidence records include SHA-256 hashes for integrity verification.</p>
            </div>
        </body>
        </html>
        """

        # Generate PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()
        return pdf_bytes

    def _generate_case_report_reportlab(
        self,
        case_data: Dict[str, Any],
        alerts: List[Dict[str, Any]],
        evidences: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]] = None
    ) -> bytes:
        """Generate PDF using ReportLab (fallback)"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        story.append(Paragraph("SIRA Compliance Report", title_style))
        story.append(Spacer(1, 20))

        # Case Info
        case_number = case_data.get("case_number", "N/A")
        title = case_data.get("title", "Untitled Case")
        status = case_data.get("status", "Unknown")
        overview = case_data.get("overview", "No overview provided")

        story.append(Paragraph(f"<b>Case Number:</b> {case_number}", styles['Normal']))
        story.append(Paragraph(f"<b>Title:</b> {title}", styles['Normal']))
        story.append(Paragraph(f"<b>Status:</b> {status}", styles['Normal']))
        story.append(Spacer(1, 20))

        story.append(Paragraph("<b>Overview:</b>", styles['Heading2']))
        story.append(Paragraph(overview, styles['Normal']))
        story.append(Spacer(1, 20))

        # Alerts Table
        story.append(Paragraph(f"<b>Associated Alerts ({len(alerts)})</b>", styles['Heading2']))

        if alerts:
            alert_data = [['ID', 'Severity', 'Description', 'Status']]
            for alert in alerts[:20]:  # Limit to 20 for PDF size
                alert_data.append([
                    str(alert.get('id', 'N/A')),
                    alert.get('severity', 'Unknown'),
                    alert.get('description', 'N/A')[:50] + '...',
                    alert.get('status', 'Unknown')
                ])

            table = Table(alert_data, colWidths=[0.5*inch, 1*inch, 3*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd'))
            ]))
            story.append(table)

        story.append(Spacer(1, 20))

        # Evidence Table
        story.append(Paragraph(f"<b>Evidence Records ({len(evidences)})</b>", styles['Heading2']))

        if evidences:
            evidence_data = [['ID', 'Type', 'Status', 'Hash']]
            for evidence in evidences[:20]:
                evidence_data.append([
                    str(evidence.get('id', 'N/A')),
                    evidence.get('evidence_type', 'Unknown'),
                    evidence.get('verification_status', 'Pending'),
                    (evidence.get('file_hash', 'N/A')[:16] + '...') if evidence.get('file_hash') else 'N/A'
                ])

            table = Table(evidence_data, colWidths=[0.5*inch, 1*inch, 1*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd'))
            ]))
            story.append(table)

        # Footer
        story.append(Spacer(1, 40))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.gray
        )
        story.append(Paragraph(
            f"Report generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            footer_style
        ))
        story.append(Paragraph(
            "This report is confidential and for authorized use only.",
            footer_style
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def generate_alert_summary_report(
        self,
        start_date: datetime,
        end_date: datetime,
        alerts: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> bytes:
        """Generate an alert summary report for a date range"""
        if self.engine == "weasyprint":
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Alert Summary Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    h1 {{ color: #2c3e50; text-align: center; }}
                    .stats {{ display: flex; justify-content: space-around; margin: 30px 0; }}
                    .stat-box {{ text-align: center; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
                    .stat-number {{ font-size: 36px; font-weight: bold; color: #3498db; }}
                    .stat-label {{ color: #666; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 30px; }}
                    th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                    th {{ background-color: #3498db; color: white; }}
                </style>
            </head>
            <body>
                <h1>Alert Summary Report</h1>
                <p style="text-align: center;">
                    {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
                </p>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-number">{stats.get('total', 0)}</div>
                        <div class="stat-label">Total Alerts</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" style="color: #e74c3c;">{stats.get('critical', 0)}</div>
                        <div class="stat-label">Critical</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" style="color: #e67e22;">{stats.get('high', 0)}</div>
                        <div class="stat-label">High</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" style="color: #27ae60;">{stats.get('resolved', 0)}</div>
                        <div class="stat-label">Resolved</div>
                    </div>
                </div>
                <h2>Alert Details</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Severity</th>
                        <th>Domain</th>
                        <th>Status</th>
                        <th>Created</th>
                    </tr>
            """

            for alert in alerts[:100]:  # Limit to 100 alerts
                html_content += f"""
                    <tr>
                        <td>{alert.get('id', 'N/A')}</td>
                        <td>{alert.get('severity', 'Unknown')}</td>
                        <td>{alert.get('domain', 'N/A')}</td>
                        <td>{alert.get('status', 'Unknown')}</td>
                        <td>{alert.get('created_at', 'N/A')}</td>
                    </tr>
                """

            html_content += """
                </table>
                <p style="text-align: center; margin-top: 40px; color: #666; font-size: 10px;">
                    Generated by SIRA Platform
                </p>
            </body>
            </html>
            """

            html = HTML(string=html_content)
            return html.write_pdf()
        else:
            # ReportLab fallback - simplified version
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph("Alert Summary Report", styles['Title']))
            story.append(Paragraph(
                f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                styles['Normal']
            ))
            story.append(Spacer(1, 20))

            story.append(Paragraph(f"Total Alerts: {stats.get('total', 0)}", styles['Normal']))
            story.append(Paragraph(f"Critical: {stats.get('critical', 0)}", styles['Normal']))
            story.append(Paragraph(f"High: {stats.get('high', 0)}", styles['Normal']))
            story.append(Paragraph(f"Resolved: {stats.get('resolved', 0)}", styles['Normal']))

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes

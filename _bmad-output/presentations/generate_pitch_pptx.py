from __future__ import annotations

import argparse
import datetime as dt
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

EMU_PER_INCH = 914400
SLIDE_W = 12192000
SLIDE_H = 6858000

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_DCMITYPE = "http://purl.org/dc/dcmitype/"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
NS_VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"

COLORS = {
    "surface_base": "E4EAF0",
    "surface_raised": "EEF2F8",
    "surface_sunken": "FFFFFF",
    "text_primary": "1A2030",
    "text_secondary": "5A6A80",
    "text_disabled": "8898A8",
    "accent": "3366FF",
    "accent_light": "6690FF",
    "accent_text": "FFFFFF",
    "status_optimal": "2E8B57",
    "status_borderline": "DAA520",
    "status_concerning": "E07020",
    "status_action": "CC3333",
    "border_dark": "A0B0C0",
    "border_light": "D0D8E4",
    "silver": "C0C0C0",
}


def emu(inches: float) -> int:
    return int(round(inches * EMU_PER_INCH))


def xml_header() -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def srgb(color: str) -> str:
    return f"<a:solidFill><a:srgbClr val=\"{color}\"/></a:solidFill>"


def line_xml(color: str | None, width: int = 12700) -> str:
    if color is None:
        return "<a:ln><a:noFill/></a:ln>"
    return f"<a:ln w=\"{width}\">{srgb(color)}</a:ln>"


def paragraph(
    text: str,
    *,
    size_pt: int = 15,
    color: str = COLORS["text_primary"],
    bold: bool = False,
    align: str = "l",
) -> str:
    attrs = [f'lang="en-US"', f'sz="{size_pt * 100}"']
    if bold:
        attrs.append('b="1"')
    ppr = "" if align == "l" else f'<a:pPr algn="{align}"/>'
    return (
        "<a:p>"
        f"{ppr}"
        f"<a:r><a:rPr {' '.join(attrs)}>{srgb(color)}</a:rPr><a:t>{escape(text)}</a:t></a:r>"
        f"<a:endParaRPr lang=\"en-US\" sz=\"{size_pt * 100}\"/>"
        "</a:p>"
    )


def text_body(
    paragraphs: list[str],
    *,
    anchor: str = "t",
    l_ins: int = 91440 // 4,
    r_ins: int = 91440 // 4,
    t_ins: int = 91440 // 4,
    b_ins: int = 91440 // 4,
) -> str:
    paras = "".join(paragraphs) if paragraphs else "<a:p/>"
    return (
        "<p:txBody>"
        f"<a:bodyPr wrap=\"square\" anchor=\"{anchor}\" lIns=\"{l_ins}\" rIns=\"{r_ins}\" "
        f"tIns=\"{t_ins}\" bIns=\"{b_ins}\"/>"
        "<a:lstStyle/>"
        f"{paras}"
        "</p:txBody>"
    )


@dataclass
class SlideBuilder:
    index: int
    shapes: list[str] = field(default_factory=list)
    next_id: int = 2

    def add_shape(
        self,
        *,
        x: int,
        y: int,
        cx: int,
        cy: int,
        fill: str | None = None,
        line: str | None = COLORS["border_dark"],
        paragraphs: list[str] | None = None,
        anchor: str = "t",
        name: str = "Shape",
        line_width: int = 12700,
    ) -> None:
        shape_id = self.next_id
        self.next_id += 1
        fill_xml = "<a:noFill/>" if fill is None else srgb(fill)
        tx_body = text_body(paragraphs or [], anchor=anchor)
        self.shapes.append(
            "<p:sp>"
            "<p:nvSpPr>"
            f"<p:cNvPr id=\"{shape_id}\" name=\"{escape(name)} {shape_id}\"/>"
            "<p:cNvSpPr/>"
            "<p:nvPr/>"
            "</p:nvSpPr>"
            "<p:spPr>"
            f"<a:xfrm><a:off x=\"{x}\" y=\"{y}\"/><a:ext cx=\"{cx}\" cy=\"{cy}\"/></a:xfrm>"
            "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
            f"{fill_xml}"
            f"{line_xml(line, line_width)}"
            "</p:spPr>"
            f"{tx_body}"
            "</p:sp>"
        )

    def add_text(
        self,
        *,
        x: int,
        y: int,
        cx: int,
        cy: int,
        paragraphs: list[str],
        anchor: str = "t",
        name: str = "Text",
    ) -> None:
        self.add_shape(
            x=x,
            y=y,
            cx=cx,
            cy=cy,
            fill=None,
            line=None,
            paragraphs=paragraphs,
            anchor=anchor,
            name=name,
        )

    def add_panel(self, *, x: int, y: int, cx: int, cy: int, title: str, body: list[str]) -> None:
        self.add_shape(
            x=x,
            y=y,
            cx=cx,
            cy=cy,
            fill=COLORS["surface_sunken"],
            line=COLORS["border_light"],
            paragraphs=[],
            name="Panel",
        )
        self.add_shape(
            x=x,
            y=y,
            cx=cx,
            cy=emu(0.04),
            fill=COLORS["accent"],
            line=None,
            paragraphs=[],
            name="Panel Accent",
        )
        self.add_text(
            x=x + emu(0.10),
            y=y + emu(0.08),
            cx=cx - emu(0.20),
            cy=cy - emu(0.16),
            paragraphs=[
                paragraph(title, size_pt=15, color=COLORS["text_primary"], bold=True),
                *body,
            ],
            name="Panel Body",
        )

    def add_callout(
        self,
        *,
        x: int,
        y: int,
        cx: int,
        cy: int,
        color: str,
        title: str,
        body: str,
    ) -> None:
        self.add_shape(
            x=x,
            y=y,
            cx=cx,
            cy=cy,
            fill=COLORS["surface_raised"],
            line=COLORS["border_light"],
            paragraphs=[],
            name="Callout Box",
        )
        self.add_shape(
            x=x,
            y=y,
            cx=emu(0.05),
            cy=cy,
            fill=color,
            line=None,
            paragraphs=[],
            name="Callout Bar",
        )
        self.add_text(
            x=x + emu(0.10),
            y=y + emu(0.08),
            cx=cx - emu(0.20),
            cy=cy - emu(0.16),
            paragraphs=[
                paragraph(title, size_pt=15, color=color, bold=True),
                paragraph(body, size_pt=14, color=COLORS["text_secondary"]),
            ],
            name="Callout Text",
        )

    def add_metric_card(
        self,
        *,
        x: int,
        y: int,
        cx: int,
        cy: int,
        label: str,
        value: str,
        copy: str,
    ) -> None:
        self.add_shape(
            x=x,
            y=y,
            cx=cx,
            cy=cy,
            fill=COLORS["surface_sunken"],
            line=COLORS["border_light"],
            paragraphs=[],
            name="Metric Card",
        )
        self.add_shape(
            x=x,
            y=y,
            cx=cx,
            cy=emu(0.05),
            fill=COLORS["accent"],
            line=None,
            paragraphs=[],
            name="Metric Accent",
        )
        self.add_text(
            x=x + emu(0.08),
            y=y + emu(0.10),
            cx=cx - emu(0.16),
            cy=cy - emu(0.18),
            paragraphs=[
                paragraph(label, size_pt=11, color=COLORS["text_secondary"], bold=True, align="ctr"),
                paragraph(value, size_pt=22, color=COLORS["text_primary"], bold=True, align="ctr"),
                paragraph(copy, size_pt=12, color=COLORS["text_secondary"], align="ctr"),
            ],
            anchor="ctr",
            name="Metric Text",
        )

    def xml(self) -> str:
        sp_tree = "".join(self.shapes)
        return (
            xml_header()
            + f"""
<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {sp_tree}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""
        )


FRAME_X = emu(0.15)
FRAME_Y = emu(0.15)
FRAME_W = SLIDE_W - FRAME_X * 2
FRAME_H = SLIDE_H - FRAME_Y * 2
HEADER_H = emu(0.18)
GAP = emu(0.08)
NAV_W = 0
STATUS_H = emu(0.28)
BODY_X = emu(0.70)
BODY_Y = emu(0.52)
BODY_W = SLIDE_W - BODY_X * 2
BODY_H = SLIDE_H - BODY_Y - STATUS_H - emu(0.32)


NAV_ITEMS = [
    "Cover",
    "Problem",
    "Users",
    "Product",
    "Loop",
    "Trust",
    "Build",
    "Model",
    "Roadmap",
    "Ask",
]


def add_shell(
    slide: SlideBuilder,
    *,
    active_nav: int,
    header_label: str,
    slide_num: int,
    status_fields: list[str],
) -> None:
    slide.add_shape(
        x=0,
        y=0,
        cx=SLIDE_W,
        cy=SLIDE_H,
        fill=COLORS["surface_base"],
        line=None,
        paragraphs=[],
        name="Background",
    )
    slide.add_shape(
        x=0,
        y=0,
        cx=SLIDE_W,
        cy=HEADER_H,
        fill=COLORS["accent"],
        line=None,
        paragraphs=[],
        name="Top Accent Bar",
    )
    slide.add_shape(
        x=BODY_X,
        y=BODY_Y + emu(1.08),
        cx=BODY_W,
        cy=emu(0.02),
        fill=COLORS["border_light"],
        line=None,
        paragraphs=[],
        name="Title Divider",
    )
    slide.add_text(
        x=BODY_X,
        y=emu(0.22),
        cx=emu(3.2),
        cy=emu(0.20),
        paragraphs=[
            paragraph("HealthCabinet", size_pt=12, color=COLORS["accent"], bold=True)
        ],
        anchor="mid",
        name="Brand",
    )
    slide.add_text(
        x=SLIDE_W - BODY_X - emu(2.20),
        y=emu(0.22),
        cx=emu(2.20),
        cy=emu(0.24),
        paragraphs=[
            paragraph(header_label, size_pt=12, color=COLORS["text_secondary"], align="r"),
            paragraph(f"{slide_num:02d}", size_pt=20, color=COLORS["text_disabled"], bold=True, align="r"),
        ],
        name="Header Meta",
    )
    footer_y = SLIDE_H - STATUS_H
    slide.add_shape(
        x=BODY_X,
        y=footer_y - emu(0.04),
        cx=BODY_W,
        cy=emu(0.02),
        fill=COLORS["border_light"],
        line=None,
        paragraphs=[],
        name="Footer Divider",
    )
    slide.add_text(
        x=BODY_X,
        y=footer_y,
        cx=emu(2.8),
        cy=STATUS_H - emu(0.02),
        paragraphs=[paragraph("HealthCabinet / Pitch Deck", size_pt=11, color=COLORS["text_disabled"])],
        anchor="mid",
        name="Footer Brand",
    )
    slide.add_text(
        x=BODY_X + emu(3.0),
        y=footer_y,
        cx=emu(5.5),
        cy=STATUS_H - emu(0.02),
        paragraphs=[paragraph(status_fields[1], size_pt=11, color=COLORS["text_secondary"], align="ctr")],
        anchor="mid",
        name="Footer Section",
    )
    slide.add_text(
        x=SLIDE_W - BODY_X - emu(1.2),
        y=footer_y,
        cx=emu(1.2),
        cy=STATUS_H - emu(0.02),
        paragraphs=[paragraph(f"{slide_num}", size_pt=11, color=COLORS["text_disabled"], align="r")],
        anchor="mid",
        name="Footer Page",
    )


def add_title_block(slide: SlideBuilder, kicker: str, title: str, subtitle: str) -> None:
    slide.add_text(
        x=BODY_X,
        y=BODY_Y,
        cx=BODY_W,
        cy=emu(1.02),
        paragraphs=[
            paragraph(kicker, size_pt=12, color=COLORS["accent"], bold=True),
            paragraph(title, size_pt=28, color=COLORS["text_primary"], bold=True),
            paragraph(subtitle, size_pt=15, color=COLORS["text_secondary"]),
        ],
        name="Title Block",
    )


def build_cover() -> tuple[str, str]:
    slide = SlideBuilder(index=1)
    add_shell(
        slide,
        active_nav=0,
        header_label="Pitch mode",
        slide_num=1,
        status_fields=["Ready", "Cover", "Current design system"],
    )
    add_title_block(
        slide,
        "HealthCabinet / Personal health intelligence",
        "Your health data, finally understood.",
        "HealthCabinet turns scattered lab PDFs and photos into structured biomarker "
        "history, trend visibility, and plain-language AI interpretation.",
    )
    card_y = BODY_Y + emu(1.45)
    card_w = emu(2.20)
    gap = emu(0.10)
    slide.add_metric_card(
        x=BODY_X,
        y=card_y,
        cx=card_w,
        cy=emu(1.15),
        label="Input",
        value="PDFs + photos",
        copy="Messy real-world documents, not idealized feeds",
    )
    slide.add_metric_card(
        x=BODY_X + card_w + gap,
        y=card_y,
        cx=card_w,
        cy=emu(1.15),
        label="Output",
        value="Trend memory",
        copy="Patient-owned health history instead of isolated files",
    )
    slide.add_metric_card(
        x=BODY_X + (card_w + gap) * 2,
        y=card_y,
        cx=card_w,
        cy=emu(1.15),
        label="Experience",
        value="Clinical UI",
        copy="Serious workstation language, not generic wellness chrome",
    )
    right_x = BODY_X + emu(6.95)
    slide.add_panel(
        x=right_x,
        y=card_y,
        cx=BODY_W - (right_x - BODY_X),
        cy=emu(2.85),
        title="What the product does",
        body=[
            paragraph("• Upload a lab document as a PDF or photo", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Extract and normalize biomarker values", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Build a readable timeline with ranges and trends", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Add plain-language AI interpretation with context", size_pt=14, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_callout(
        x=BODY_X,
        y=card_y + emu(1.35),
        cx=emu(6.65),
        cy=emu(1.50),
        color=COLORS["accent"],
        title="Why this matters",
        body="Labs give people numbers. HealthCabinet gives them memory, interpretation, "
        "and continuity across time.",
    )
    return "Cover", slide.xml()


def build_problem() -> tuple[str, str]:
    slide = SlideBuilder(index=2)
    add_shell(
        slide,
        active_nav=1,
        header_label="Problem framing",
        slide_num=2,
        status_fields=["Ready", "Problem", "Fragmented data -> missing meaning"],
    )
    add_title_block(
        slide,
        "Health data exists. Meaning does not.",
        "Patients own the files, but not the longitudinal understanding.",
        "The strongest opportunity is not generating more health data. It is turning existing "
        "documents into a coherent patient-owned timeline.",
    )
    top = BODY_Y + emu(1.45)
    left_w = emu(4.95)
    slide.add_panel(
        x=BODY_X,
        y=top,
        cx=left_w,
        cy=emu(3.15),
        title="Current reality",
        body=[
            paragraph("• Results arrive as PDFs, scans, screenshots, and paper printouts.", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Each lab is interpreted as a snapshot, not a timeline.", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Users google abnormal values and still leave uncertain.", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Chronic-condition users repeat the same confusion every few months.", size_pt=14, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_panel(
        x=BODY_X + left_w + emu(0.12),
        y=top,
        cx=BODY_W - left_w - emu(0.12),
        cy=emu(3.15),
        title="What needs to replace it",
        body=[
            paragraph("• Patient-owned health memory", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Cross-upload pattern recognition", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• Plain-language interpretation instead of raw flags alone", size_pt=14, color=COLORS["text_secondary"]),
            paragraph("• One coherent timeline instead of portal-by-portal fragmentation", size_pt=14, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_callout(
        x=BODY_X,
        y=top + emu(3.30),
        cx=emu(4.95),
        cy=emu(1.00),
        color=COLORS["status_borderline"],
        title="User pain is repetitive",
        body="The best starting user is not a novelty uploader. It is the person who keeps testing "
        "and never gets a patient-owned longitudinal view.",
    )
    slide.add_callout(
        x=BODY_X + emu(5.10),
        y=top + emu(3.30),
        cx=BODY_W - emu(5.10),
        cy=emu(1.00),
        color=COLORS["accent"],
        title="The opportunity is continuity",
        body="HealthCabinet does not invent more health data. It transforms existing documents into "
        "compounding intelligence people can actually use.",
    )
    return "Problem", slide.xml()


def build_users() -> tuple[str, str]:
    slide = SlideBuilder(index=3)
    add_shell(
        slide,
        active_nav=2,
        header_label="Target users",
        slide_num=3,
        status_fields=["Ready", "Users", "Repeated testers prioritized"],
    )
    add_title_block(
        slide,
        "Start where the history compounds",
        "Repeated testers are the highest-value starting segment.",
        "The product gets stronger when the user returns with another document. That makes the "
        "early user wedge unusually clear.",
    )
    top = BODY_Y + emu(1.45)
    box_w = emu(3.50)
    gap = emu(0.12)
    titles = ["Sofia", "Maks", "Founder/Admin"]
    copies = [
        [
            paragraph("Primary persona", size_pt=12, color=COLORS["accent"], bold=True),
            paragraph("Hashimoto's patient testing every quarter. She needs trend intelligence she can "
                      "carry into appointments, not another file archive.", size_pt=13, color=COLORS["text_secondary"]),
        ],
        [
            paragraph("Secondary persona", size_pt=12, color=COLORS["text_primary"], bold=True),
            paragraph("Private self-tester who wants plain-language explanation without panic or guesswork.",
                      size_pt=13, color=COLORS["text_secondary"]),
        ],
        [
            paragraph("Operational persona", size_pt=12, color=COLORS["status_borderline"], bold=True),
            paragraph("Needs visibility into upload failures, extraction quality, and correction workflows "
                      "without heavy ops overhead.", size_pt=13, color=COLORS["text_secondary"]),
        ],
    ]
    for idx, title in enumerate(titles):
        slide.add_panel(
            x=BODY_X + idx * (box_w + gap),
            y=top,
            cx=box_w,
            cy=emu(2.50),
            title=title,
            body=copies[idx],
        )
    slide.add_callout(
        x=BODY_X,
        y=top + emu(2.68),
        cx=emu(5.35),
        cy=emu(1.10),
        color=COLORS["status_optimal"],
        title="Why repeated testers matter",
        body="They create exactly the type of longitudinal history that makes the product differentiated. "
        "Every upload deepens the moat.",
    )
    slide.add_callout(
        x=BODY_X + emu(5.47),
        y=top + emu(2.68),
        cx=BODY_W - emu(5.47),
        cy=emu(1.10),
        color=COLORS["accent"],
        title="Why the wedge is practical",
        body="This is a clear B2C starting point with understandable repeat behavior and visible value "
        "after every new document.",
    )
    return "Users", slide.xml()


def build_product() -> tuple[str, str]:
    slide = SlideBuilder(index=4)
    add_shell(
        slide,
        active_nav=3,
        header_label="Product flow",
        slide_num=4,
        status_fields=["Ready", "Product", "Import -> extract -> interpret"],
    )
    add_title_block(
        slide,
        "Upload once. Understand immediately. Learn over time.",
        "The product translates documents into a timeline users can actually read.",
        "The experience is deliberately table-first and clinically legible, rather than card-heavy "
        "or decorative.",
    )
    top = BODY_Y + emu(1.42)
    card_w = emu(2.62)
    gap = emu(0.10)
    steps = [
        ("1", "Import document", "User uploads a PDF or photo from any lab."),
        ("2", "Extract values", "Pipeline reads, normalizes, and scores confidence."),
        ("3", "Show history", "Dashboard updates status, ranges, and trends."),
        ("4", "Explain clearly", "AI adds plain-language interpretation with context."),
    ]
    for idx, (num, title, copy) in enumerate(steps):
        x = BODY_X + idx * (card_w + gap)
        slide.add_shape(
            x=x,
            y=top,
            cx=card_w,
            cy=emu(1.35),
            fill=COLORS["surface_raised"],
            line=COLORS["border_dark"],
            paragraphs=[],
            name="Step Card",
        )
        slide.add_shape(
            x=x + emu(0.08),
            y=top + emu(0.08),
            cx=emu(0.24),
            cy=emu(0.24),
            fill=COLORS["accent"],
            line=None,
            paragraphs=[paragraph(num, size_pt=12, color=COLORS["accent_text"], bold=True, align="ctr")],
            anchor="ctr",
            name="Step Number",
        )
        slide.add_text(
            x=x + emu(0.40),
            y=top + emu(0.08),
            cx=card_w - emu(0.48),
            cy=emu(1.10),
            paragraphs=[
                paragraph(title, size_pt=14, color=COLORS["text_primary"], bold=True),
                paragraph(copy, size_pt=12, color=COLORS["text_secondary"]),
            ],
            name="Step Copy",
        )
    slide.add_panel(
        x=BODY_X,
        y=top + emu(1.55),
        cx=emu(5.25),
        cy=emu(2.25),
        title="Pipeline status language",
        body=[
            paragraph("• Uploading: store the document and start orchestration", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Reading: parse image/PDF content", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Extracting: map values and ranges into structure", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Generating: produce AI interpretation", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_callout(
        x=BODY_X + emu(5.40),
        y=top + emu(1.55),
        cx=BODY_W - emu(5.40),
        cy=emu(1.00),
        color=COLORS["status_borderline"],
        title="Edge cases are first-class",
        body="Partial extraction is preserved and the user gets a guided retry instead of a dead end.",
    )
    slide.add_callout(
        x=BODY_X + emu(5.40),
        y=top + emu(2.70),
        cx=BODY_W - emu(5.40),
        cy=emu(1.00),
        color=COLORS["status_optimal"],
        title="The UI stays dense and legible",
        body="Status, reference ranges, and trend live in the table. Users do not have to open "
        "three layers of cards to understand one biomarker.",
    )
    return "Product", slide.xml()


def build_loop() -> tuple[str, str]:
    slide = SlideBuilder(index=5)
    add_shell(
        slide,
        active_nav=4,
        header_label="Compounding loop",
        slide_num=5,
        status_fields=["Ready", "Loop", "Compounding product value"],
    )
    add_title_block(
        slide,
        "Import -> understand -> trust the platform more",
        "Each upload increases product value instead of merely creating another record.",
        "The retention engine is simple: the product becomes more useful because the history gets "
        "denser and the context gets stronger.",
    )
    top = BODY_Y + emu(1.42)
    card_w = emu(2.60)
    gap = emu(0.10)
    cards = [
        ("Step 1", "Upload", "Any lab document enters the system."),
        ("Step 2", "Structure", "Values become queryable history."),
        ("Step 3", "Interpret", "AI explains the latest picture clearly."),
        ("Step 4", "Compound", "The next upload becomes more valuable."),
    ]
    for idx, (label, value, copy) in enumerate(cards):
        slide.add_metric_card(
            x=BODY_X + idx * (card_w + gap),
            y=top,
            cx=card_w,
            cy=emu(1.15),
            label=label,
            value=value,
            copy=copy,
        )
    slide.add_panel(
        x=BODY_X,
        y=top + emu(1.35),
        cx=emu(5.15),
        cy=emu(2.40),
        title="Why retention can work",
        body=[
            paragraph("• The product gains context with each new document.", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Trend visibility becomes stronger after the second and third upload.", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• AI can reason across time instead of summarizing isolated data.", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• The user starts to rely on HealthCabinet as their memory layer.", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_panel(
        x=BODY_X + emu(5.30),
        y=top + emu(1.35),
        cx=BODY_W - emu(5.30),
        cy=emu(2.40),
        title="Not just another AI wrapper",
        body=[
            paragraph("• Arbitrary document intake instead of narrow lab integrations", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Cross-upload memory as a core behavior", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Dense clinical table UI as part of product language", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Admin correction workflow for real-world extraction edge cases", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    return "Loop", slide.xml()


def build_trust() -> tuple[str, str]:
    slide = SlideBuilder(index=6)
    add_shell(
        slide,
        active_nav=5,
        header_label="Trust and safety",
        slide_num=6,
        status_fields=["Ready", "Trust", "EU posture + AI guardrails"],
    )
    add_title_block(
        slide,
        "Sensitive product, serious handling",
        "The trust model is part of the product, not a footer afterthought.",
        "Health products fail when safety and control are treated as polish instead of product behavior.",
    )
    top = BODY_Y + emu(1.42)
    slide.add_panel(
        x=BODY_X,
        y=top,
        cx=emu(5.25),
        cy=emu(2.55),
        title="Data and compliance posture",
        body=[
            paragraph("• AWS eu-central-1 target", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Consent, export, and deletion flows in scope", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Encryption posture for health data and tokens", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• No casual treatment of special-category health data", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_panel(
        x=BODY_X + emu(5.40),
        y=top,
        cx=BODY_W - emu(5.40),
        cy=emu(2.55),
        title="AI safety posture",
        body=[
            paragraph("• Informational, not diagnostic", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Uncertainty should be surfaced, not hidden", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• No treatment or dosage instruction framing", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Human review path exists for extraction edge cases", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_callout(
        x=BODY_X,
        y=top + emu(2.75),
        cx=emu(3.45),
        cy=emu(1.10),
        color=COLORS["status_optimal"],
        title="Patient trust",
        body="Users need to believe their history is secure, exportable, and under their control.",
    )
    slide.add_callout(
        x=BODY_X + emu(3.58),
        y=top + emu(2.75),
        cx=emu(3.45),
        cy=emu(1.10),
        color=COLORS["status_borderline"],
        title="Operational trust",
        body="Admin tools matter because document intelligence will always have edge cases.",
    )
    slide.add_callout(
        x=BODY_X + emu(7.16),
        y=top + emu(2.75),
        cx=BODY_W - emu(7.16),
        cy=emu(1.10),
        color=COLORS["accent"],
        title="Brand trust",
        body="The clinical UI helps, but real credibility comes from bounded claims and visible safety choices.",
    )
    return "Trust", slide.xml()


def build_build() -> tuple[str, str]:
    slide = SlideBuilder(index=7)
    add_shell(
        slide,
        active_nav=6,
        header_label="Build status",
        slide_num=7,
        status_fields=["Ready", "Build", "Repo-backed product story"],
    )
    add_title_block(
        slide,
        "This is not deck-only positioning",
        "There is already product surface in the repository.",
        "The pitch should describe an existing direction with working surfaces, not a hypothetical disconnected from the codebase.",
    )
    top = BODY_Y + emu(1.42)
    slide.add_panel(
        x=BODY_X,
        y=top,
        cx=emu(5.20),
        cy=emu(2.85),
        title="System shape",
        body=[
            paragraph("• Frontend: SvelteKit 2, Svelte 5, table-first clinical UI", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Backend API: FastAPI, SQLAlchemy async, auth, document endpoints", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Worker: ARQ pipeline for async document processing", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Storage: PostgreSQL + MinIO / S3-compatible object storage", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_panel(
        x=BODY_X + emu(5.35),
        y=top,
        cx=BODY_W - emu(5.35),
        cy=emu(2.85),
        title="Visible repo capabilities",
        body=[
            paragraph("• Authentication and consent-aware signup", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Medical onboarding and profile capture", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Document upload and status streaming", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Dashboard trends, AI clinical notes, and admin operations", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_callout(
        x=BODY_X,
        y=top + emu(3.05),
        cx=BODY_W,
        cy=emu(0.95),
        color=COLORS["accent"],
        title="Credibility point",
        body="The pitch describes a repo-backed product direction with real application surfaces, not an empty strategy artifact.",
    )
    return "Build", slide.xml()


def build_model() -> tuple[str, str]:
    slide = SlideBuilder(index=8)
    add_shell(
        slide,
        active_nav=7,
        header_label="Business model",
        slide_num=8,
        status_fields=["Ready", "Model", "Freemium first"],
    )
    add_title_block(
        slide,
        "Validate the core loop before overbuilding monetization",
        "Freemium proves trust first. Premium layers onto real repeat usage.",
        "The immediate goal is not complicated billing. It is proving that people return because the product becomes more useful over time.",
    )
    top = BODY_Y + emu(1.42)
    slide.add_panel(
        x=BODY_X,
        y=top,
        cx=emu(5.30),
        cy=emu(2.75),
        title="Commercial model",
        body=[
            paragraph("• Free tier proves the upload-to-insight loop", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Paid tier unlocks deeper AI memory and richer trend history", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Premium workflows layer on top of proven trust and retention", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Family plans and upgrades become stronger after the core loop wins", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_panel(
        x=BODY_X + emu(5.45),
        y=top,
        cx=BODY_W - emu(5.45),
        cy=emu(2.75),
        title="Go-to-market wedge",
        body=[
            paragraph("• Chronic-condition communities with repeated testing behavior", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Private lab and self-testing audiences already buying panels", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Founder-led demos and story-driven product marketing", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Memorable clinical-workstation aesthetic as a positioning advantage", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    return "Model", slide.xml()


def build_roadmap() -> tuple[str, str]:
    slide = SlideBuilder(index=9)
    add_shell(
        slide,
        active_nav=8,
        header_label="Roadmap",
        slide_num=9,
        status_fields=["Ready", "Roadmap", "Compound depth, not feature sprawl"],
    )
    add_title_block(
        slide,
        "Prove the loop, then deepen the intelligence",
        "The roadmap compounds depth instead of scattering into disconnected features.",
        "The right next moves reinforce the existing upload-to-insight loop rather than diluting it.",
    )
    top = BODY_Y + emu(1.42)
    slide.add_callout(
        x=BODY_X,
        y=top,
        cx=emu(3.45),
        cy=emu(1.15),
        color=COLORS["accent"],
        title="Now",
        body="Improve upload reliability, time-to-first-insight, and extraction confidence.",
    )
    slide.add_callout(
        x=BODY_X + emu(3.58),
        y=top,
        cx=emu(3.45),
        cy=emu(1.15),
        color=COLORS["status_optimal"],
        title="Next",
        body="Increase repeat usage, deeper timelines, and stronger cross-document AI memory.",
    )
    slide.add_callout(
        x=BODY_X + emu(7.16),
        y=top,
        cx=BODY_W - emu(7.16),
        cy=emu(1.15),
        color=COLORS["status_borderline"],
        title="Later",
        body="Doctor-share workflows, richer exports, premium layers, and broader EU expansion.",
    )
    slide.add_panel(
        x=BODY_X,
        y=top + emu(1.35),
        cx=emu(5.30),
        cy=emu(2.45),
        title="What to measure first",
        body=[
            paragraph("• Upload success rate", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Time to first usable insight", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Repeat uploads across separate dates", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Users with multi-document histories", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_panel(
        x=BODY_X + emu(5.45),
        y=top + emu(1.35),
        cx=BODY_W - emu(5.45),
        cy=emu(2.45),
        title="What not to optimize too early",
        body=[
            paragraph("• Complex billing surface before trust is proven", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Feature sprawl that weakens the core loop", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Marketing polish detached from product usefulness", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• Medical overclaiming for short-term attention", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    return "Roadmap", slide.xml()


def build_ask() -> tuple[str, str]:
    slide = SlideBuilder(index=10)
    add_shell(
        slide,
        active_nav=9,
        header_label="Closing ask",
        slide_num=10,
        status_fields=["Ready", "Ask", "Pilot users + critique + partners"],
    )
    add_title_block(
        slide,
        "HealthCabinet is ready for sharper feedback loops",
        "The next step is evidence: pilot users, stronger critique, and the right conversations.",
        "The product story is clearer now. What it needs next is better proof with real users and real documents.",
    )
    top = BODY_Y + emu(1.42)
    slide.add_callout(
        x=BODY_X,
        y=top,
        cx=emu(3.45),
        cy=emu(1.15),
        color=COLORS["accent"],
        title="Need 1",
        body="Pilot users with recurring lab workflows",
    )
    slide.add_callout(
        x=BODY_X + emu(3.58),
        y=top,
        cx=emu(3.45),
        cy=emu(1.15),
        color=COLORS["status_optimal"],
        title="Need 2",
        body="Design and product critique on the current UX direction",
    )
    slide.add_callout(
        x=BODY_X + emu(7.16),
        y=top,
        cx=BODY_W - emu(7.16),
        cy=emu(1.15),
        color=COLORS["status_borderline"],
        title="Need 3",
        body="Strategic conversations around patient-facing health intelligence",
    )
    slide.add_panel(
        x=BODY_X,
        y=top + emu(1.35),
        cx=emu(5.20),
        cy=emu(2.50),
        title="Why now",
        body=[
            paragraph("• The product story is clear and differentiated", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• The design language is memorable and domain-aligned", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• The repo already contains real product surfaces", size_pt=13, color=COLORS["text_secondary"]),
            paragraph("• The next proof needed is repeat usage with real documents", size_pt=13, color=COLORS["text_secondary"]),
        ],
    )
    slide.add_callout(
        x=BODY_X + emu(5.35),
        y=top + emu(1.35),
        cx=BODY_W - emu(5.35),
        cy=emu(2.50),
        color=COLORS["accent"],
        title="Closing line",
        body="HealthCabinet is not trying to be another wellness surface. It is trying to become "
        "the patient-owned memory and interpretation layer for recurring health data.",
    )
    return "Ask", slide.xml()


SLIDE_BUILDERS = [
    build_cover,
    build_problem,
    build_users,
    build_product,
    build_loop,
    build_trust,
    build_build,
    build_model,
    build_roadmap,
    build_ask,
]


def content_types_xml(slide_count: int) -> str:
    slide_overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    return (
        xml_header()
        + f"""
<Types xmlns="{NS_CT}">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
{slide_overrides}
</Types>
"""
    )


def root_rels_xml() -> str:
    return (
        xml_header()
        + f"""
<Relationships xmlns="{NS_REL}">
  <Relationship Id="rId1" Type="{NS_R}/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="{NS_R}/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""
    )


def app_xml(titles: list[str]) -> str:
    titles_xml = "".join(f"<vt:lpstr>{escape(title)}</vt:lpstr>" for title in titles)
    return (
        xml_header()
        + f"""
<Properties xmlns="{NS_EP}" xmlns:vt="{NS_VT}">
  <Application>Codex</Application>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Slides>{len(titles)}</Slides>
  <Notes>0</Notes>
  <HiddenSlides>0</HiddenSlides>
  <MMClips>0</MMClips>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Slides</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>{len(titles)}</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="{len(titles)}" baseType="lpstr">
      {titles_xml}
    </vt:vector>
  </TitlesOfParts>
  <Company></Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""
    )


def core_xml() -> str:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        xml_header()
        + f"""
<cp:coreProperties xmlns:cp="{NS_CP}" xmlns:dc="{NS_DC}" xmlns:dcterms="{NS_DCTERMS}" xmlns:dcmitype="{NS_DCMITYPE}" xmlns:xsi="{NS_XSI}">
  <dc:title>HealthCabinet Pitch Deck</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
"""
    )


def presentation_xml(slide_count: int) -> str:
    slide_ids = "\n".join(
        f'    <p:sldId id="{256 + i}" r:id="rId{i + 2}"/>'
        for i in range(slide_count)
    )
    return (
        xml_header()
        + f"""
<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
{slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle>
    <a:defPPr/>
    <a:lvl1pPr marL="0" indent="0"><a:defRPr sz="1800" lang="en-US"/></a:lvl1pPr>
    <a:lvl2pPr marL="0" indent="0"><a:defRPr sz="1600" lang="en-US"/></a:lvl2pPr>
    <a:lvl3pPr marL="0" indent="0"><a:defRPr sz="1400" lang="en-US"/></a:lvl3pPr>
  </p:defaultTextStyle>
</p:presentation>
"""
    )


def presentation_rels_xml(slide_count: int) -> str:
    slide_rels = "\n".join(
        f'  <Relationship Id="rId{i + 2}" Type="{NS_R}/slide" Target="slides/slide{i + 1}.xml"/>'
        for i in range(slide_count)
    )
    return (
        xml_header()
        + f"""
<Relationships xmlns="{NS_REL}">
  <Relationship Id="rId1" Type="{NS_R}/slideMaster" Target="slideMasters/slideMaster1.xml"/>
{slide_rels}
</Relationships>
"""
    )


def slide_master_xml() -> str:
    return (
        xml_header()
        + f"""
<p:sldMaster xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld name="HealthCabinet Master">
    <p:bg>
      <p:bgPr>
        {srgb(COLORS["surface_base"])}
        <a:effectLst/>
      </p:bgPr>
    </p:bg>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="2147483649" r:id="rId1"/>
  </p:sldLayoutIdLst>
  <p:txStyles>
    <p:titleStyle>
      <a:lvl1pPr algn="l"><a:defRPr sz="3000" b="1" lang="en-US"/></a:lvl1pPr>
    </p:titleStyle>
    <p:bodyStyle>
      <a:lvl1pPr marL="0" indent="0"><a:defRPr sz="1800" lang="en-US"/></a:lvl1pPr>
      <a:lvl2pPr marL="0" indent="0"><a:defRPr sz="1600" lang="en-US"/></a:lvl2pPr>
      <a:lvl3pPr marL="0" indent="0"><a:defRPr sz="1400" lang="en-US"/></a:lvl3pPr>
    </p:bodyStyle>
    <p:otherStyle>
      <a:lvl1pPr marL="0" indent="0"><a:defRPr sz="1400" lang="en-US"/></a:lvl1pPr>
    </p:otherStyle>
  </p:txStyles>
</p:sldMaster>
"""
    )


def slide_master_rels_xml() -> str:
    return (
        xml_header()
        + f"""
<Relationships xmlns="{NS_REL}">
  <Relationship Id="rId1" Type="{NS_R}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="{NS_R}/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""
    )


def slide_layout_xml() -> str:
    return (
        xml_header()
        + f"""
<p:sldLayout xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" type="blank" preserve="1">
  <p:cSld name="Blank">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"""
    )


def slide_layout_rels_xml() -> str:
    return (
        xml_header()
        + f"""
<Relationships xmlns="{NS_REL}">
  <Relationship Id="rId1" Type="{NS_R}/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"""
    )


def theme_xml() -> str:
    return (
        xml_header()
        + f"""
<a:theme xmlns:a="{NS_A}" name="HealthCabinet Theme">
  <a:themeElements>
    <a:clrScheme name="HealthCabinet">
      <a:dk1><a:srgbClr val="{COLORS["text_primary"]}"/></a:dk1>
      <a:lt1><a:srgbClr val="{COLORS["surface_sunken"]}"/></a:lt1>
      <a:dk2><a:srgbClr val="{COLORS["text_secondary"]}"/></a:dk2>
      <a:lt2><a:srgbClr val="{COLORS["surface_raised"]}"/></a:lt2>
      <a:accent1><a:srgbClr val="{COLORS["accent"]}"/></a:accent1>
      <a:accent2><a:srgbClr val="{COLORS["status_optimal"]}"/></a:accent2>
      <a:accent3><a:srgbClr val="{COLORS["status_borderline"]}"/></a:accent3>
      <a:accent4><a:srgbClr val="{COLORS["status_concerning"]}"/></a:accent4>
      <a:accent5><a:srgbClr val="{COLORS["status_action"]}"/></a:accent5>
      <a:accent6><a:srgbClr val="{COLORS["accent_light"]}"/></a:accent6>
      <a:hlink><a:srgbClr val="{COLORS["accent"]}"/></a:hlink>
      <a:folHlink><a:srgbClr val="{COLORS["accent_light"]}"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="HealthCabinet">
      <a:majorFont><a:latin typeface="DM Sans"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="DM Sans"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="HealthCabinet">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
        <a:solidFill><a:schemeClr val="lt2"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="dk2"/></a:solidFill><a:prstDash val="solid"/></a:ln>
        <a:ln w="25400" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="dk2"/></a:solidFill><a:prstDash val="solid"/></a:ln>
        <a:ln w="38100" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="dk2"/></a:solidFill><a:prstDash val="solid"/></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="lt1"/></a:solidFill>
        <a:solidFill><a:schemeClr val="lt2"/></a:solidFill>
        <a:solidFill><a:schemeClr val="bg1"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/>
  <a:extraClrSchemeLst/>
</a:theme>
"""
    )


def slide_rels_xml() -> str:
    return (
        xml_header()
        + f"""
<Relationships xmlns="{NS_REL}">
  <Relationship Id="rId1" Type="{NS_R}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""
    )


def write_pptx(output_path: Path) -> None:
    slides = [builder() for builder in SLIDE_BUILDERS]
    titles = [title for title, _ in slides]
    slide_xmls = [xml for _, xml in slides]
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(len(slide_xmls)))
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("docProps/app.xml", app_xml(titles))
        zf.writestr("docProps/core.xml", core_xml())
        zf.writestr("ppt/presentation.xml", presentation_xml(len(slide_xmls)))
        zf.writestr("ppt/_rels/presentation.xml.rels", presentation_rels_xml(len(slide_xmls)))
        zf.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml())
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels_xml())
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml())
        zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels_xml())
        zf.writestr("ppt/theme/theme1.xml", theme_xml())
        for idx, slide_xml in enumerate(slide_xmls, start=1):
            zf.writestr(f"ppt/slides/slide{idx}.xml", slide_xml)
            zf.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", slide_rels_xml())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a native PPTX pitch deck for HealthCabinet.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("healthcabinet-pitch-deck.pptx"),
        help="Output PPTX path",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_pptx(args.output)
    print(args.output)


if __name__ == "__main__":
    main()

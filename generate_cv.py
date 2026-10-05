#!/usr/bin/env python3
"""
Generador de CV en PDF (sin dependencias externas).
Produce un PDF 1.4 válido con layout profesional de una página,
usando las fuentes base Helvetica (Type1) incluidas en todos los lectores.
"""

import zlib

PAGE_W, PAGE_H = 595.28, 841.89  # A4 en puntos
MARGIN_L = 50
MARGIN_R = 50
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

# Colores (RGB 0-1)
ACCENT = (0.11, 0.33, 0.56)   # azul profundo
DARK = (0.13, 0.13, 0.13)
GRAY = (0.40, 0.40, 0.40)
LIGHT = (0.60, 0.60, 0.60)
RULE = (0.80, 0.82, 0.85)

# ---- Métricas de anchura para Helvetica (AFM widths / 1000) ----
HELV_WIDTHS = {
    ' ':278,'!':278,'"':355,'#':556,'$':556,'%':889,'&':667,"'":191,'(':333,')':333,
    '*':389,'+':584,',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,
    '4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':278,';':278,'<':584,'=':584,
    '>':584,'?':556,'@':1015,'A':667,'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,
    'H':722,'I':278,'J':500,'K':667,'L':556,'M':833,'N':722,'O':778,'P':667,'Q':778,
    'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,'X':667,'Y':667,'Z':611,'[':278,
    '\\':278,']':278,'^':469,'_':556,'`':333,'a':556,'b':556,'c':500,'d':556,'e':556,
    'f':278,'g':556,'h':556,'i':222,'j':222,'k':500,'l':222,'m':833,'n':556,'o':556,
    'p':556,'q':556,'r':333,'s':500,'t':278,'u':556,'v':500,'w':722,'x':500,'y':500,
    'z':500,'{':334,'|':260,'}':334,'~':584,
}
# Bold es ligeramente más ancho; usamos factor aproximado para unos pocos
HELVB_WIDTHS = dict(HELV_WIDTHS)
for k in HELVB_WIDTHS:
    HELVB_WIDTHS[k] = min(1000, int(HELVB_WIDTHS[k] * 1.05) + 10)

# Mapa de caracteres acentuados -> WinAnsi (usaremos encoding WinAnsiEncoding)
# fpdf-like: en WinAnsiEncoding los acentos tienen códigos > 127.
WINANSI = {
    'á':'\xe1','é':'\xe9','í':'\xed','ó':'\xf3','ú':'\xfa','ñ':'\xf1',
    'Á':'\xc1','É':'\xc9','Í':'\xcd','Ó':'\xd3','Ú':'\xda','Ñ':'\xd1',
    'ü':'\xfc','Ü':'\xdc','·':'\xb7','–':'\x96','—':'\x97',
    '“':'\x93','”':'\x94','‘':'\x91','’':'\x92','…':'\x85',
    '°':'\xb0','€':'\x80',
}
# ancho por defecto para acentuados = ancho de la letra base aproximado
ACCENT_WIDTH_BASE = {
    'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n','Á':'A','É':'E','Í':'I',
    'Ó':'O','Ú':'U','Ñ':'N','ü':'u','Ü':'U','·':'.','–':'-','—':'-',
    '“':'"','”':'"','‘':"'",'’':"'",'…':'.','°':'o','€':'E',
}


def char_width(ch, size, bold=False):
    table = HELVB_WIDTHS if bold else HELV_WIDTHS
    if ch in table:
        return table[ch] * size / 1000.0
    base = ACCENT_WIDTH_BASE.get(ch)
    if base and base in table:
        return table[base] * size / 1000.0
    return 556 * size / 1000.0  # fallback


def text_width(s, size, bold=False):
    return sum(char_width(c, size, bold) for c in s)


def encode_text(s):
    out = []
    for ch in s:
        if ch in WINANSI:
            out.append(WINANSI[ch])
        elif ord(ch) < 128:
            out.append(ch)
        else:
            base = ACCENT_WIDTH_BASE.get(ch, '?')
            out.append(base if ord(base) < 128 else '?')
    return ''.join(out)


def pdf_escape(s):
    return s.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')


def wrap_text(s, size, max_w, bold=False):
    words = s.split(' ')
    lines, cur = [], ''
    for w in words:
        trial = w if not cur else cur + ' ' + w
        if text_width(trial, size, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class PDFCanvas:
    def __init__(self):
        self.ops = []
        self.y = PAGE_H - 48

    def set_color(self, rgb):
        self.ops.append(f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} rg")

    def set_stroke(self, rgb):
        self.ops.append(f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} RG")

    def line(self, x1, y1, x2, y2, w=0.8):
        self.ops.append(f"{w:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def text(self, x, y, s, size, bold=False, color=DARK, tracking=0.0):
        font = "F2" if bold else "F1"
        self.set_color(color)
        enc = pdf_escape(encode_text(s))
        tc = f" {tracking:.2f} Tc" if tracking else ""
        self.ops.append(f"BT /{font} {size} Tf{tc} {x:.2f} {y:.2f} Td ({enc}) Tj ET")
        if tracking:
            self.ops.append("BT 0 Tc ET")

    # ---------- bloques de alto nivel ----------
    def heading(self, title):
        self.y -= 6
        self.text(MARGIN_L, self.y, title, 10.5, bold=True, color=ACCENT, tracking=1.2)
        self.y -= 5
        self.set_stroke(RULE)
        self.line(MARGIN_L, self.y, PAGE_W - MARGIN_R, self.y, 0.8)
        self.y -= 13

    def paragraph(self, s, size=9, color=DARK, leading=12.5, indent=0):
        for ln in wrap_text(s, size, CONTENT_W - indent):
            self.text(MARGIN_L + indent, self.y, ln, size, color=color)
            self.y -= leading
        self.y -= 1

    def bullet(self, s, size=9, color=DARK, leading=12.0):
        bx = MARGIN_L + 4
        tx = MARGIN_L + 14
        lines = wrap_text(s, size, CONTENT_W - 14)
        self.set_color(ACCENT)
        self.ops.append(f"BT /F2 {size} Tf {bx:.2f} {self.y:.2f} Td (\x95) Tj ET")
        for i, ln in enumerate(lines):
            self.text(tx, self.y, ln, size, color=color)
            self.y -= leading
        self.y -= 1

    def entry(self, title, meta, desc=None):
        # title (bold) + meta (gray, right)
        self.text(MARGIN_L, self.y, title, 9.3, bold=True, color=DARK)
        if meta:
            mw = text_width(meta, 8.2)
            self.text(PAGE_W - MARGIN_R - mw, self.y, meta, 8.2, color=GRAY)
        self.y -= 12
        if desc:
            for ln in wrap_text(desc, 8.6, CONTENT_W - 6):
                self.text(MARGIN_L + 6, self.y, ln, 8.6, color=GRAY)
                self.y -= 11
        self.y -= 3

    def gap(self, h):
        self.y -= h


def build_cv():
    c = PDFCanvas()

    # ---------- ENCABEZADO ----------
    name = "ALEX ISRAEL PERALTA MARTÍNEZ"
    c.text(MARGIN_L, c.y, name, 20, bold=True, color=ACCENT, tracking=0.5)
    c.y -= 20
    c.text(MARGIN_L, c.y, "Desarrollador de Software Jr.  ·  QA  ·  Sistemas  ·  Redes Sociales",
           10, color=GRAY)
    c.y -= 17
    contact = "Tel. 814 535 9906   |   aipm.1001@gmail.com   |   El Pueblito, Querétaro"
    c.text(MARGIN_L, c.y, contact, 8.8, color=DARK)
    c.y -= 8
    c.set_stroke(ACCENT)
    c.line(MARGIN_L, c.y, PAGE_W - MARGIN_R, c.y, 1.6)
    c.y -= 16

    # ---------- PERFIL ----------
    c.heading("PERFIL PROFESIONAL")
    c.paragraph(
        "Estudiante que inicia su formación en Desarrollo de Software / Ingeniería en "
        "Computación, con fuerte motivación por construir una carrera en tecnología. Cuento "
        "con bases en fundamentos del desarrollo de software y herramientas de IA, "
        "complementadas con experiencia laboral previa que me dio disciplina, atención al "
        "detalle y hábito de trabajar bajo estándares y pruebas de funcionamiento. Busco una "
        "oportunidad como trainee/junior en desarrollo, QA, soporte de sistemas o gestión de "
        "redes sociales, donde pueda aprender, aportar y crecer a largo plazo."
    )

    # ---------- OBJETIVO ----------
    c.heading("OBJETIVO PROFESIONAL")
    c.paragraph(
        "Integrarme a un equipo de tecnología para iniciar y consolidar mi trayectoria, "
        "desarrollando habilidades sólidas en programación, aseguramiento de calidad (QA) y "
        "sistemas, mientras curso mis estudios. Mi meta es evolucionar de un rol junior hacia "
        "un perfil de desarrollador autónomo y confiable."
    )

    # ---------- HABILIDADES TÉCNICAS ----------
    c.heading("HABILIDADES TÉCNICAS")
    skills = [
        "Fundamentos de programación y desarrollo de software",
        "Lógica y resolución de problemas",
        "Nociones de QA: pruebas y validación de funcionamiento",
        "Herramientas de IA (Google AI)",
        "Ofimática (Word, Excel, correo)",
        "Manejo de redes sociales y contenido digital",
    ]
    # dos columnas
    col_w = CONTENT_W / 2
    start_y = c.y
    half = (len(skills) + 1) // 2
    left, right = skills[:half], skills[half:]
    yy = start_y
    for s in left:
        c.set_color(ACCENT)
        c.ops.append(f"BT /F2 9 Tf {MARGIN_L+2:.2f} {yy:.2f} Td (\x95) Tj ET")
        c.text(MARGIN_L + 12, yy, s, 8.8, color=DARK)
        yy -= 13.5
    yy2 = start_y
    rx = MARGIN_L + col_w
    for s in right:
        c.set_color(ACCENT)
        c.ops.append(f"BT /F2 9 Tf {rx+2:.2f} {yy2:.2f} Td (\x95) Tj ET")
        c.text(rx + 12, yy2, s, 8.8, color=DARK)
        yy2 -= 13.5
    c.y = min(yy, yy2) - 2

    # ---------- FORMACIÓN ----------
    c.heading("FORMACIÓN Y CURSOS")
    c.entry("Ingeniería en Computación / Desarrollo de Software — Nivel superior",
            "Ingreso próximo",
            "Estudiante de nuevo ingreso.")
    c.entry("Fundamentos del Desarrollo de Software — Gobierno de México (constancia oficial)",
            "Abr 2025 – May 2025",
            "Introducción a la lógica de programación, bases del desarrollo y buenas prácticas.")
    c.entry("Fundamentos de Google AI — INFOTEC, vía Coursera (constancia)",
            "Sep 2026",
            "Conceptos de inteligencia artificial y uso de herramientas de IA aplicadas.")
    c.entry("Bachillerato — Escuela Preparatoria Oficial del Edo. de México (EPOEM 81)",
            "Egreso 2019")
    c.entry("Carrera Técnica en Electricidad y Mantenimiento Industrial (trunca) — ICATI",
            "Ago – Oct 2022")

    # ---------- EXPERIENCIA ----------
    c.heading("EXPERIENCIA · COMPETENCIAS TRANSFERIBLES")
    c.paragraph(
        "Experiencia técnica en entornos industriales donde desarrollé habilidades directamente "
        "aplicables a tecnología: seguir procedimientos y estándares, realizar pruebas de "
        "funcionamiento (mentalidad QA), diagnóstico y resolución de problemas con atención al detalle.",
        size=8.6, color=GRAY, leading=11.5)
    c.gap(2)
    c.entry("Técnico Eléctrico — Apoyo en Instalación y Mantenimiento",
            "Ingeniería Profesional Aplicada RIBA",
            "Pruebas de funcionamiento de equipos, cumplimiento de normas de seguridad y trabajo en equipo para asegurar la continuidad operativa.")
    c.entry("Apoyo Técnico en Mantenimiento Industrial",
            "Esp. en Mantenimiento Ind. y Sistemas Automatizados S.A. de C.V.",
            "Montaje de equipos y validación de sistemas automatizados bajo estándares.")
    c.entry("Auxiliar Eléctrico y de Construcción",
            "Proyectos Electr y Constr, S.A.",
            "Tendido de cableado y diagnóstico de instalaciones, aplicando precisión y seguridad.")

    # ---------- COMPETENCIAS PERSONALES + IDIOMAS ----------
    c.heading("COMPETENCIAS PERSONALES")
    c.paragraph(
        "Aprendizaje rápido  ·  Trabajo en equipo  ·  Responsabilidad  ·  Atención al detalle  ·  "
        "Disciplina  ·  Proactividad", size=9, color=DARK)

    c.heading("IDIOMAS")
    c.paragraph("Español — Nativo        |        Inglés — Básico (A2), escrito y hablado",
                size=9, color=DARK)

    return c.ops


def assemble_pdf(ops, path):
    content = "\n".join(ops).encode('latin-1', 'replace')
    comp = zlib.compress(content)

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
        f"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>".encode()
    )
    objects.append(
        b"<< /Length " + str(len(comp)).encode() + b" /Filter /FlateDecode >>\nstream\n"
        + comp + b"\nendstream"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_pos = len(out)
    n = len(objects) + 1
    out += f"xref\n0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n"
    out += f"<< /Size {n} /Root 1 0 R >>\n".encode()
    out += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"

    with open(path, 'wb') as f:
        f.write(out)
    print(f"PDF escrito: {path} ({len(out)} bytes)")


if __name__ == "__main__":
    ops = build_cv()
    assemble_pdf(ops, "CV_Alex_Peralta.pdf")
